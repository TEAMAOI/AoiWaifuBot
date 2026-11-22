from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from aoiwaifu import *
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import asyncio
import logging
backup_logger = logging.getLogger('BACKUP')

class AutoBackup:

    def __init__(self):
        self.source_client = ddw
        self.backup_client = backup_ddw
        self.db_name = DB_NAME
        self.owner_id = OWNER_ID
        self.backup_interval_hours = 24
        self.max_backups = 3

    async def get_backup_db_name(self, date_str=None):
        """Generate backup database name with date"""
        if not date_str:
            date_str = datetime.now().strftime('%d_%m_%Y')
        return f'{self.db_name}_{date_str}'

    async def check_last_backup(self):
        """Check when the last backup was created"""
        try:
            db_list = await self.backup_client.list_database_names()
            backup_dbs = [db for db in db_list if db.startswith(f'{self.db_name}_')]
            if not backup_dbs:
                backup_logger.info('No previous backups found')
                return None
            backup_dbs.sort(reverse=True)
            latest_backup = backup_dbs[0]
            date_part = latest_backup.replace(f'{self.db_name}_', '')
            try:
                backup_date = datetime.strptime(date_part, '%d_%m_%Y')
                backup_logger.info(f'Latest backup found: {latest_backup} from {backup_date}')
                return backup_date
            except ValueError:
                backup_logger.error(f'Invalid backup date format: {date_part}')
                return None
        except Exception as e:
            backup_logger.error(f'Error checking last backup: {e}')
            return None

    async def create_backup(self):
        """Create a new backup of the database"""
        try:
            backup_logger.info('Starting database backup...')
            backup_db_name = await self.get_backup_db_name()
            backup_db = self.backup_client[backup_db_name]
            source_db = self.source_client[self.db_name]
            collections = await source_db.list_collection_names()
            backup_logger.info(f'Found {len(collections)} collections to backup')
            total_docs = 0
            for collection_name in collections:
                source_collection = source_db[collection_name]
                backup_collection = backup_db[collection_name]
                documents = []
                async for doc in source_collection.find():
                    documents.append(doc)
                if documents:
                    await backup_collection.insert_many(documents)
                    total_docs += len(documents)
                    backup_logger.info(f'Backed up {len(documents)} documents from {collection_name}')
            backup_logger.info(f'Backup completed successfully! Total documents: {total_docs}')
            await self.send_backup_notification(backup_db_name, total_docs, len(collections))
            await self.cleanup_old_backups()
            return True
        except Exception as e:
            backup_logger.error(f'Error creating backup: {e}')
            await self.send_error_notification(str(e))
            return False

    async def cleanup_old_backups(self):
        """Remove backups older than max_backups days"""
        try:
            db_list = await self.backup_client.list_database_names()
            backup_dbs = [db for db in db_list if db.startswith(f'{self.db_name}_')]
            if len(backup_dbs) <= self.max_backups:
                return
            backup_dates = []
            for db_name in backup_dbs:
                date_part = db_name.replace(f'{self.db_name}_', '')
                try:
                    backup_date = datetime.strptime(date_part, '%d_%m_%Y')
                    backup_dates.append((backup_date, db_name))
                except ValueError:
                    continue
            backup_dates.sort()
            while len(backup_dates) > self.max_backups:
                old_date, old_db_name = backup_dates.pop(0)
                await self.backup_client.drop_database(old_db_name)
                backup_logger.info(f'Deleted old backup: {old_db_name}')
        except Exception as e:
            backup_logger.error(f'Error cleaning up old backups: {e}')

    async def send_backup_notification(self, backup_name, total_docs, total_collections):
        """Send backup success notification to owner"""
        try:
            message = f"✅ **Database Backup Completed**\n\n📅 **Backup Name:** `{backup_name}`\n📊 **Collections:** {total_collections}\n📄 **Documents:** {total_docs}\n⏰ **Time:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n🔒 **Status:** Your data is safely backed up!"
            await app.send_message(chat_id=self.owner_id, text=message)
            backup_logger.info('Backup notification sent to owner')
        except Exception as e:
            backup_logger.error(f'Error sending backup notification: {e}')

    async def send_error_notification(self, error_msg):
        """Send backup error notification to owner"""
        try:
            message = f"❌ **Database Backup Failed**\n\n🚨 **Error:** {error_msg}\n⏰ **Time:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n⚠️ Please check the backup system!"
            await app.send_message(chat_id=self.owner_id, text=message)
            backup_logger.error('Backup error notification sent to owner')
        except Exception as e:
            backup_logger.error(f'Error sending error notification: {e}')

    async def should_create_backup(self):
        """Check if a new backup should be created"""
        last_backup = await self.check_last_backup()
        if not last_backup:
            backup_logger.info('No previous backup found, creating first backup')
            return True
        time_since_backup = datetime.now() - last_backup
        if time_since_backup >= timedelta(hours=self.backup_interval_hours):
            backup_logger.info(f'Time for new backup (last backup: {time_since_backup} ago)')
            return True
        backup_logger.info(f'Backup not needed yet (last backup: {time_since_backup} ago)')
        return False

    async def start_auto_backup(self):
        """Start the automatic backup system"""
        backup_logger.info('Auto backup system started')
        if await self.should_create_backup():
            await self.create_backup()
        while True:
            try:
                await asyncio.sleep(3600)
                if await self.should_create_backup():
                    await self.create_backup()
            except Exception as e:
                backup_logger.error(f'Error in auto backup loop: {e}')
                await asyncio.sleep(3600)
backup_system = AutoBackup()

@app.on_message(filters.command('backup'))
@require_power('VIP')
async def manual_backup(client: Client, message: Message):
    """Manual backup command for admins"""
    lang = await get_effective_lang(message)
    try:
        processing_msg = await message.reply_text(tr('🔄 Creating manual backup...', lang))
        success = await backup_system.create_backup()
        if success:
            await processing_msg.edit_text(tr('✅ Manual backup completed successfully!', lang))
        else:
            await processing_msg.edit_text(tr('❌ Manual backup failed! Check logs for details.', lang))
    except Exception as e:
        await message.reply_text(tr(f'❌ Error creating manual backup: {str(e)}', lang))

@app.on_message(filters.command('backupstatus'))
@require_power('VIP')
async def backup_status(client: Client, message: Message):
    """Check backup system status"""
    lang = await get_effective_lang(message)
    try:
        last_backup = await backup_system.check_last_backup()
        if last_backup:
            time_since = datetime.now() - last_backup
            status_msg = f"📊 **Backup System Status**\n\n✅ **Last Backup:** {last_backup.strftime('%d/%m/%Y %H:%M:%S')}\n⏰ **Time Since:** {time_since}\n🔄 **Next Backup:** {('Soon' if time_since >= timedelta(hours=24) else 'In ' + str(timedelta(hours=24) - time_since))}\n📁 **Max Backups:** {backup_system.max_backups} days\n🔧 **Status:** Active"
        else:
            status_msg = f'📊 **Backup System Status**\n\n❌ **Last Backup:** No backups found\n🔄 **Next Backup:** Will create first backup soon\n📁 **Max Backups:** {backup_system.max_backups} days\n🔧 **Status:** Active'
        await message.reply_text(tr(status_msg, lang))
    except Exception as e:
        await message.reply_text(tr(f'❌ Error checking backup status: {str(e)}', lang))

@app.on_message(filters.command('listbackups'))
@require_power('VIP')
async def list_backups(client: Client, message: Message):
    """List all available backups"""
    lang = await get_effective_lang(message)
    try:
        db_list = await backup_system.backup_client.list_database_names()
        backup_dbs = [db for db in db_list if db.startswith(f'{backup_system.db_name}_')]
        if not backup_dbs:
            await message.reply_text(tr('📁 No backups found.', lang))
            return
        backup_info = []
        for db_name in backup_dbs:
            date_part = db_name.replace(f'{backup_system.db_name}_', '')
            try:
                backup_date = datetime.strptime(date_part, '%d_%m_%Y')
                backup_info.append((backup_date, db_name))
            except ValueError:
                continue
        backup_info.sort(reverse=True)
        backup_list = '📁 **Available Backups:**\n\n'
        for i, (backup_date, db_name) in enumerate(backup_info, 1):
            age = datetime.now() - backup_date
            backup_list += f"{i}. `{db_name}`\n   📅 {backup_date.strftime('%d/%m/%Y')}\n   ⏰ {age.days} days ago\n\n"
        await message.reply_text(tr(backup_list, lang))
    except Exception as e:
        await message.reply_text(tr(f'❌ Error listing backups: {str(e)}', lang))

@app.on_message(filters.command('startbackup'))
@require_power('OWNER')
async def start_backup_system_command(client: Client, message: Message):
    """Start the backup system manually (Owner only)"""
    lang = await get_effective_lang(message)
    try:
        processing_msg = await message.reply_text(tr('🔄 Starting backup system...', lang))
        asyncio.create_task(backup_system.start_auto_backup())
        await processing_msg.edit_text(tr('✅ Backup system started successfully!', lang))
        backup_logger.info('Backup system started manually by owner')
    except Exception as e:
        await message.reply_text(tr(f'❌ Error starting backup system: {str(e)}', lang))
        backup_logger.error(f'Error starting backup system: {e}')
from aoiwaifu import *
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
