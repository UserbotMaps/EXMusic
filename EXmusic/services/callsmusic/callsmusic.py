from typing import Dict

from pytgcalls import GroupCall
from pytgcalls import PyTgCalls

from EXmusic.services.queues.queues import queues
from pyrogram import client

instances: Dict[int, GroupCall] = {}
active_chats: Dict[int, Dict[str, bool]] = {}

pytgcalls = PyTgCalls(client)


def init_instance(chat_id: int):
    if chat_id not in instances:
        instances[chat_id] = GroupCall(client)

    instance = instances[chat_id]

    @instance.on_playout_ended
    async def ___(__, _):
        queues.task_done(chat_id)

        if queues.is_empty(chat_id):
            await stop(chat_id)
        else:
            instance.input_filename = queues.get(chat_id)["file"]


def get_instance(chat_id: int) -> GroupCall:
    init_instance(chat_id)
    return instances[chat_id]


async def start(chat_id: int):
    await get_instance(chat_id).start(chat_id)
    active_chats[chat_id] = {"playing": True, "muted": False}


async def stop(chat_id: int):
    await get_instance(chat_id).stop()

    if chat_id in active_chats:
        del active_chats[chat_id]


async def set_stream(chat_id: int, file: str):
    if chat_id not in active_chats:
        await start(chat_id)
    get_instance(chat_id).input_filename = file


def pause(chat_id: int) -> bool:
    if chat_id not in active_chats:
        return False
    elif not active_chats[chat_id]["playing"]:
        return False

    get_instance(chat_id).pause_playout()
    active_chats[chat_id]["playing"] = False
    return True


def resume(chat_id: int) -> bool:
    if chat_id not in active_chats:
        return False
    elif active_chats[chat_id]["playing"]:
        return False

    get_instance(chat_id).resume_playout()
    active_chats[chat_id]["playing"] = True
    return True


def mute(chat_id: int) -> int:
    if chat_id not in active_chats:
        return 2
    elif active_chats[chat_id]["muted"]:
        return 1

    get_instance(chat_id).set_is_mute(True)
    active_chats[chat_id]["muted"] = True
    return 0


def unmute(chat_id: int) -> int:
    if chat_id not in active_chats:
        return 2
    elif not active_chats[chat_id]["muted"]:
        return 1

    get_instance(chat_id).set_is_mute(False)
    active_chats[chat_id]["muted"] = False
    return 0

@pytgcalls.on_stream_end()
def on_stream_end(chat_id: int) -> None:
    queues.task_done(chat_id)

    if queues.is_empty(chat_id):
        pytgcalls.leave_group_call(chat_id)
    else:
        pytgcalls.change_stream(chat_id, queues.get(chat_id)["file"])


run = pytgcalls.run
