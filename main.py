import asyncio
import os
import sys
import redis
import time
from pyrogram import Client, idle
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram.handlers import MessageHandler, ChatMemberUpdatedHandler
from pyrogram.session.session import Session
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database


# Genera sessione pyro
async def pyro(token):
    Session.notice_displayed = True

    API_HASH = ''
    API_ID = ''

    bot_id = str(token).split(':')[0]
    app = Client(
        'sessioni/session_bot' + str(bot_id),
        api_hash=API_HASH,
        api_id=API_ID,
        bot_token=token,
        workers=20,
        sleep_threshold=30
    )
    return app

async def chat_handler(bot, update):
    old_member = update.old_chat_member
    new_member = update.new_chat_member
    if old_member and not old_member.user.id == bot_id: return
    if new_member and not new_member.user.id == bot_id: return 
    if update.chat.type == ChatType.CHANNEL:
        try: await bot.leave_chat(chat_id=update.chat.id)
        except Exception as e: pass
        return
    if (not update.old_chat_member or update.old_chat_member.status == ChatMemberStatus.BANNED): # controllo se l'evento è specificamente di aggiunta
        members=await bot.get_chat_members_count(update.chat.id)
        if members<50:
            await bot.send_message(update.chat.id, "Mi dispiace, il bot è abilitato solamente per gruppi con almeno 50 utenti, riaggiungilo quando avrai raggiunto quella soglia, per qualsiasi chiarimento @nukleodev")
            await bot.leave_chat(chat_id=update.chat.id)
        elif update.chat.type == ChatType.GROUP:
            await bot.send_message(update.chat.id, "Mi dispiace, il bot è abilitato solamente per SUPERGRUPPI, riaggiungilo quando avrai reso questo gruppo un supergruppo, per qualsiasi chiarimento @nukleodev")
            await bot.leave_chat(chat_id=update.chat.id)
        else:
            await bot.send_message(update.chat.id, "Hai aggiunto TagAllBot con successo!\nDa ora gli admin del gruppo potranno usare /all per taggare tutti i membri del gruppo!\n\nSe ritieni che questo sia fastidioso per te ti basterà fare /escludimi per venir escluso dalla lista dei tag\n\nPer qualsiasi problema @nukleodev")
    return

async def bot_handler(bot, message):
    tipo = message.chat.type
    if message.media or message.service: return
    text = str(message.text)
    chatid = message.chat.id
    userid = message.from_user.id
    if text == '/start' or text == '/start@tagga_tuttibot':
        last_time=redis.get(userid)
        if last_time:
            elapsed_time = time.time() - float(last_time)
            if elapsed_time<antiflood: return
        redis.set(userid, time.time())
        await db.adduser(userid)
        if tipo==ChatType.PRIVATE:
            tagged = await db.getBeTagged(userid)
            text=f"👋🏻 Benvenuto in TagAll, con questo bot puoi taggare tutti i membri dei gruppi dove sei admin semplicemente lanciando /all!\n\nPuoi escluderti dal venir taggato globalmente con /escludimi\nStato attuale: {'🟢 Incluso' if tagged[0]==1 else '🔴 Escluso'}\n\nCreato da @nukleodev"
            await bot.send_message(chatid, text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Aggiungi ora TagAll Bot!",url="https://t.me/tagga_tuttibot?startgroup")]]))
        else:
            await bot.send_message(chatid, "Hai aggiunto TagAllBot con successo!\nDa ora gli admin del gruppo potranno usare /all per taggare tutti i membri del gruppo!\n\nSe ritieni che questo sia fastidioso per te ti basterà fare /escludimi per venir escluso dalla lista dei tag\n\nPer qualsiasi problema @nukleodev")


    elif text == "/escludimi" or text == "/escludimi@tagga_tuttibot":
        last_time=redis.get(userid)
        if last_time:
            elapsed_time = time.time() - float(last_time)
            if elapsed_time<antiflood: return
        redis.set(userid, time.time())
        await db.adduser(userid)
        await db.updateBeTagged(False, userid)
        await message.reply_text("✖️ Ok da ora sarai escluso dal venir taggato da questo bot, usa /includimi per tornare in lista globalmente.", quote=True)

    elif text == "/includimi" or text == "/includimi@tagga_tuttibot":
        last_time=redis.get(userid)
        if last_time:
            elapsed_time = time.time() - float(last_time)
            if elapsed_time<antiflood: return
        redis.set(userid, time.time())
        await db.adduser(userid)
        await db.updateBeTagged(True, userid)
        await message.reply_text("✔️ Ok da ora sarai incluso nel venir taggato da questo bot, usa /escludimi per uscire dalla lista globalmente.", quote=True)

    elif text == "/all" or text == "/all@tagga_tuttibot" or text == "@all":
        last_time=redis.get(userid)
        if last_time:
            elapsed_time = time.time() - float(last_time)
            if elapsed_time<antiflood: return
        redis.set(userid, time.time())
        if tipo==ChatType.PRIVATE:
            await bot.send_message(chatid, "🙅‍♂️ Comando usabile solo nei gruppi")
        else:
            member = await bot.get_chat_member(chatid, userid)
            if member.status == ChatMemberStatus.OWNER or member.status == ChatMemberStatus.ADMINISTRATOR:
                last_time=redis.get(chatid)
                if last_time:
                    elapsed_time = time.time() - float(last_time)
                    remaining_time = max(0, 7200 - elapsed_time)
                    if remaining_time>0:
                        await message.reply_text(f"⏳ Puoi usare un tagall ogni 120 minuti (2 ore), mancano ancora {int(remaining_time/60)} minuti.")
                        return
                redis.set(chatid, time.time())
                await bot.send_message(chatid, "🚨 Inizio operazione di Tag All")
                asyncio.create_task(taggaTutti(bot, chatid, message.reply_to_message))
    return


async def taggaTutti(bot, chatid, reply):
    users = []

    async for x in bot.get_chat_members(chatid):
        if not x.user.is_bot:
            tagged = await db.getBeTagged(x.user.id)
            if tagged is None or tagged[0]==1:
                    users.append((x.user.first_name, x.user.id))

    tags = [f"<a href='tg://user?id={user[1]}'>{user[0]}</a>" for user in users]

    chunks = [tags[i:i + 5] for i in range(0, len(tags), 5)]
    for y in chunks:
        if reply:
            await bot.send_message(chatid,' '.join(y),reply_to_message_id=reply.id)
        else:
            await bot.send_message(chatid,' '.join(y))
        await asyncio.sleep(2)

    await bot.send_message(chatid, f"✅ Tag All completato con successo, taggati esattamente {len(users)} membri.")

    return

async def main():

    print(f'Genero sessione > ', end='')
    SESSION = await pyro(token=TOKEN)
    HANDLERS = {
        'msg': MessageHandler(bot_handler),
        'chat': ChatMemberUpdatedHandler(chat_handler)
    }
    SESSION.add_handler(HANDLERS['msg'])
    SESSION.add_handler(HANDLERS['chat'])


    print('avvio > ', end='')
    await SESSION.start()

    print('avviati!')
    await idle()

    print('Stopping > ', end='')
    await SESSION.stop()

    await db.close()
    loop.stop()
    print('stopped!\n')
    exit()



if __name__ == '__main__':
    TOKEN = ''
    bot_id = int(TOKEN.split(':')[0])
    loop = asyncio.get_event_loop()
    db = Database(loop=loop)
    antiflood=3
    redis = redis.Redis(host='localhost', port=6379, db=15)
    loop.run_until_complete(main())
    exit()
