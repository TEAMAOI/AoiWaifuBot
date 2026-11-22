import asyncio
import importlib
import inspect
from pyrogram import idle
from aoiwaifu import *
from aoiwaifu.modules import ALL_MODULES
from aoiwaifu.admin import ALL_ADMIN_MODULES

# Reuse the single main event loop across Motor, PTB, and Kurigram/Pyrogram.
loop = mongo_loop
asyncio.set_event_loop(loop)


async def _async_main() -> None:
    running_loop = asyncio.get_running_loop()

    # Keep Motor clients bound to the active running loop.
    for motor_client in (ddw, backup_ddw):
        try:
            motor_client.get_io_loop = _get_current_io_loop
            if hasattr(motor_client, "io_loop"):
                motor_client.io_loop = running_loop
        except Exception:
            pass

    # Align Pyrogram/Kurigram client and dispatcher loop attributes if exposed.
    if getattr(AOI, "loop", None) is not None and AOI.loop is not running_loop:
        try:
            AOI.loop = running_loop
        except Exception:
            pass
    if getattr(getattr(AOI, "dispatcher", None), "loop", None) is not None:
        try:
            AOI.dispatcher.loop = running_loop
        except Exception:
            pass

    # PTB Application is used for InlineQueryHandler.
    # Pyrogram/Kurigram remains the single Telegram update receiver.
    await application.initialize()
    if application.post_init:
        await application.post_init(application)
    await application.start()

    start_res = AOI.start()
    if inspect.isawaitable(start_res):
        await start_res

    LOGGER("aoiwaifu").info(
        "╔═══════════════════════════════════════════════╗\n"
        "║             🌸  AOI WAIFU BOT  🌸             ║\n"
        "║         Anime Character Catcher Bot           ║\n"
        "╚═══════════════════════════════════════════════╝"
    )
    await asyncio.to_thread(send_start_message)

    try:
        idle_res = idle()
        if inspect.isawaitable(idle_res):
            await idle_res
    finally:
        if getattr(AOI, "is_connected", False):
            stop_res = AOI.stop()
            if inspect.isawaitable(stop_res):
                await stop_res

        if application.running:
            await application.stop()
        await application.shutdown()


def main() -> None:
    for module_name in ALL_MODULES:
        importlib.import_module("aoiwaifu.modules." + module_name)

    for admin_module_name in ALL_ADMIN_MODULES:
        importlib.import_module("aoiwaifu.admin." + admin_module_name)

    LOGGER("aoiwaifu").info(
        "🌸 Loaded %d user modules and %d admin modules successfully!",
        len(ALL_MODULES),
        len(ALL_ADMIN_MODULES),
    )

    try:
        loop.run_until_complete(_async_main())
    finally:
        if not loop.is_closed():
            loop.close()


if __name__ == "__main__":
    main()
