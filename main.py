import asyncio
import os
import sys
import threading
import time

from TikTokApi import TikTokApi
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = '5322171250:AAGm8vFQnhomWVCm7VKU6QxLiEVbV8C-bTQ'
HELP_MESSAGE = "Welcome to TikTokTracker bot! This bot allows you to track followers amount in your TikTok account\n" \
               "\nTo add account to track use `/add <username> <password>`\n" \
               "\nTo delete account from tracking list use `/delete <username> <password>`\n" \
               "\nTo get list of your accounts with subscribers use `/list_accounts`\n" \
               "\nTo change the delay in seconds between server calls (30 by default) use `/delay_seconds <seconds>`" \
               "\nTo get your user_id use `/my_user_id`\n\nBot won't work if your user_id is not in a magic list.\n" \
               "\nIf you are not in magic list contact @itproger008"

WRONG_INPUT_MESSAGE = "Your query is not properly formatted"
ACCOUNT_NOT_EXISTS_MESSAGE = "This account does not exist"
DEFAULT_DELAY = 30

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
magic_list = []

users = dict()
delays = dict()

tiktok = TikTokApi()


def read_ids():
    ids_file = open("ids.txt", "r")
    for s in ids_file.readlines():
        magic_list.append(s.replace('\n', ''))
    ids_file.close()


def read_savings():
    global users, delays

    in_users = list(os.walk(sys.path[0] + "\\users"))[0][2]
    for u in in_users:
        accounts = []
        u_file = open("users/" + u, 'r')
        for s in u_file.readlines():
            accounts.append(s.replace('\n', ''))
        u_file.close()
        users[u.replace(".txt", "")] = {"accounts": accounts}

    in_delays = list(os.walk(sys.path[0] + "\\delays"))[0][2]
    for d in in_delays:
        cur = []
        d_file = open("delays/" + d, 'r')
        for s in d_file.readlines():
            cur.append(s.replace('\n', ''))
        d_file.close()
        delays[d.replace(".txt", "")] = cur[0]

    print(users)
    print(delays)


def is_authorized(tg_user_id):
    res = magic_list.__contains__(str(tg_user_id))
    return res


async def reply(in_message, message):
    await bot.send_message(in_message.from_user.id, message)


async def send_message(tg_user_id, message):
    await bot.send_message(tg_user_id, message)


def exists(username):
    user = tiktok.user(username)
    return len(user.info_full()) != 0


@dp.message_handler(commands=['start', 'help'])
async def send_help(message: types.Message):
    await bot.send_message(message.chat.id, HELP_MESSAGE)


@dp.message_handler(commands=['my_user_id'])
async def user_id(message: types.Message):
    await reply(message, "Your user_id: " + str(message.from_user.id))


@dp.message_handler(commands=['add'])
async def add_user(message: types.Message):
    if not is_authorized(message.from_user.id):
        await reply(message, "You are not in magic list. Contact @itproger008")
        return

    parts: str = message.text.split("/add ")
    if len(parts) != 2 or len(parts[1]) == 0:
        await reply(message, WRONG_INPUT_MESSAGE)
        return

    username = parts[1].split(' ')[0]
    if len(parts[1].split(' ')) != 2:
        await reply(message, WRONG_INPUT_MESSAGE)
        return

    if not exists(username):
        await reply(message, ACCOUNT_NOT_EXISTS_MESSAGE)
        return

    if users.__contains__(str(message.from_user.id)):
        prev = users[str(message.from_user.id)]["accounts"]
    else:
        prev = []

    if not delays.__contains__(str(message.from_user.id)):
        delays[message.from_user.id] = DEFAULT_DELAY
        update_delays(message.from_user.id)

    prev.append(parts[1])
    users[str(message.from_user.id)] = {"accounts": prev}

    update_users(message.from_user.id)
    await reply(message, "Account successfully added")
    print("Account " + username + " added to " + str(message.from_user.id))
    # await send_message(message, str(users))


@dp.message_handler(commands=['delete'])
async def remove_user(message: types.Message):
    if not is_authorized(message.from_user.id):
        await reply(message, "You are not in magic list. Contact @itproger008")
        return

    parts: str = message.text.split("/delete ")
    if len(parts) != 2 or len(parts[1]) == 0:
        await reply(message, WRONG_INPUT_MESSAGE)
        return

    if users.__contains__(str(message.from_user.id)):
        prev = users[str(message.from_user.id)]["accounts"]
    else:
        prev = []

    try:
        prev.remove(parts[1])

        users[message.from_user.id] = {"accounts": prev}

        update_users(message.from_user.id)
        await reply(message, "Account successfully removed")
    except:
        await reply(message, "Error. Not deleted.")


@dp.message_handler(commands=['delay_seconds'])
async def delay_seconds(message: types.Message):
    if not is_authorized(message.from_user.id):
        await reply(message, "You are not in magic list. Contact @itproger008")
        return

    parts: str = message.text.split("/delay_seconds ")
    if len(parts) != 2 or len(parts[1]) == 0:
        await reply(message, WRONG_INPUT_MESSAGE)
        return

    delays[message.from_user.id] = int(parts[1])
    update_delays(message.from_user.id)

    await reply(message, "Delay successfully changed")
    # await send_message(message, str(users))


@dp.message_handler(commands=['list_accounts'])
async def list_accounts(message: types.Message):
    tg_user_id = message.from_user.id
    if not users.__contains__(str(tg_user_id)):
        await reply(message, "No accounts found")
        return

    repl = ""

    try:
        for pair in users[str(tg_user_id)]["accounts"]:
            username = pair.split(' ')[0]
            password = pair.split(' ')[1]
            try:
                f = followers_amount(username)
                repl += username + ' ' + password + " - " + str(f) + '\n'
                repl += "tiktok.com/@" + username + "\n\n"
            except:
                repl = "Check account " + username + "\ntiktok.com/@" + username
                print("Deleting account " + pair)
                users[str(tg_user_id)]["accounts"].remove(pair)

        await reply(message, repl)
    except:
        await reply(message, "No accounts found")


def followers_amount(username):
    user = tiktok.user(username)
    print("Checking " + username)
    return int(user.info_full()["stats"]["followerCount"])


def check_one_thousand(pair):
    username = pair.split(' ')[0]
    followers = followers_amount(username)
    return followers >= 1000


def write_to_file(path, strings):
    f = open(path, "w+")
    f.truncate(0)
    for s in strings:
        f.write(s + '\n')

    f.close()


def update_delays(tg_user_id):
    write_to_file("delays/" + str(tg_user_id) + ".txt", [str(delays[tg_user_id])])


def update_users(tg_user_id):
    print(users)
    write_to_file("users/" + str(tg_user_id) + ".txt", users[str(tg_user_id)]["accounts"])


def start_tracking():
    cur = 0
    while True:
        time.sleep(1)

        for k in list(delays.keys()):
            if cur % int(delays[k]) == 0:
                for pair in users[str(k)]["accounts"]:
                    is_thousand_reached = False
                    try:
                        is_thousand_reached = check_one_thousand(pair)
                    except:
                        is_thousand_reached = False
                        print("Problem")

                    if is_thousand_reached:
                        new_bot = Bot(API_TOKEN)
                        asyncio.run(
                            new_bot.send_message(k, "Account `" + pair + "` reached 1K followers"))
                        asyncio.run(new_bot.session.close())  # Falls down. )= sam daun chmo obossanoe)))))))))))
                        # delays.pop(k)
                        try:
                            users[k]["accounts"].remove(pair)
                            update_users(k)
                        except ValueError:
                            print(users)
                            print("Wasn't added so was't removed")

        cur += 1
        if cur >= pow(2, 30):
            cur = 0
            print("Time reached its limit and set to 0")


if __name__ == '__main__':
    read_savings()
    read_ids()
    threading.Thread(target=start_tracking).start()
    executor.start_polling(dp, skip_updates=True)
