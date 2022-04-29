import telebot
import numpy as np
import pandas as pd
import re
import datetime
import random
import pymorphy2
from telebot import types
from collections import defaultdict

from harrypotter_faiss_answer import Searcher
from quests_to_user import get_suggest, end_q


searcher = Searcher(debug=False)

# answers_path = './answers.txt'

# answers = []
# with open(answers_path) as f:
#     for line in f:
#         answers.append(line.strip())
# ans_len = len(answers)

token = '5234187834:AAGIBmuXTQjKvmrzFylonLFpOW48t-P3w-I'
bot = telebot.TeleBot(token)

unknown_message = "Привет!\nЧтобы начать общение напиши /start\nЧтобы получить помощь напиши /help\n\
                     Чтобы закрыть меня -- /stop"
dummy_message = "Я Вас не понял!"

welcome_message = "Я -- бот, который может обсудить с тобой любую тему, связанную с Гарри Поттером : \
начиная c непростительных заклинаний, заканчивая линой жизнью персонажей. Спроси меня что-нибудь!"

goodby_message = "Прощай! Хоггвартс всегда будет ждать тебя!"

# df = pd.read_csv('./dataframe_hp.csv')
df = pd.read_csv('./df_hp_v5.csv')
# df.drop(columns=['date_of_birth_x'], inplace=True)

add_names = ['desc', 'another_name', 'date_of_birth_y', 'eye_color', 'patronus', 'wife', 'facultet', 'death',
             'age', 'location']
name_to_features = {}
name_to_features = {k : {x : str(y) for x, y in zip(add_names, v)} for k, v in zip(df['name'].values.tolist(), df[add_names].values.tolist())}
tmp = {}
morph = pymorphy2.MorphAnalyzer()
for k, v in name_to_features.items():
    k_new = morph.parse(k)[0]
    if "NOUN" in k_new.tag and "anim" == k_new.tag.animacy:
        k_new = k_new.normal_form
    else:
        k_new = k
    tmp[k_new] = v
    a_nn = v['another_name']
    if type(a_nn) == list:
        for a_n in a_nn:
            if str(a_n) != 'nan':
                tmp[str(a_n)] = v
    else:
        if str(a_nn) != 'nan':
            a_n = a_nn.split(',')
            for aa_nn in a_n:
                aa_nn_new = morph.parse(str(aa_nn))[0].normal_form
                tmp[aa_nn_new] = v

name_to_features = tmp

names_sorted = sorted([k for k in name_to_features.keys()], key=len, reverse=True)

descr_list = [r'кто такой', r'кто такая', r'кто такие', r'что такое', r'кто это такой', r'кто это', r'что это', r'это',
              r'что знаешь про', r'что думаешь про', r'что знаешь о', r'что знаешь', r'что думаешь о', r'что думаешь']
death_list = [r'когда умер', r'когда умерла', r'в каком (году|месяце) умер', r'в каком (году|месяце) умерла',
              r'дата смерти', r'когда день смерти', r'день смерти', r'жив ли', r'умер ли', r'жив', r'умер']
birth_list = [r'когда родился', r'когда родилась', r'в каком (году|месяце) родился', r'в каком (году|месяце) родилась',
              r'дата рождения', r'когда день рождения', r'день рождения']
eye_list = [r'какие цветом глаза', r'какого цвета у .+ глаза', r'какой цвет глаз', r'какие глаза', r'глаза у',
            r'у .+ глаза']
patronus_list = [r'какой патронус', r'какой патронус', r'патронус']
wife_list = [r'как зовут жену', r'как звали жену', r'как зовут мужа', r'как звали мужа', r'муж у',
             r'жена у', r'кто муж', r'кто жена', r'кто супруг', r'кто супруга']
facultet_list = [r"на каком факультете", r"в каком факультете", r'факультет у']
age_list = [r'сколько лет', r'какой возраст', r'возраст у', r'возраст']
location_list = [r'где находится', r'в каком городе', r'в какой стране', r'в какой страна', r'в каком город',
                 r'где']
another_name_list = [r'None']

key_to_quest = {
    'desc' : descr_list,
    'death' : death_list,
    'date_of_birth' : birth_list,
    'eye_color' : eye_list,
    'patronus' : patronus_list,
    'wife' : wife_list,
    'facultet' : facultet_list,
    'another_name' : another_name_list,
    'age' : age_list,
    'location' : location_list
}
quest_to_key = {vv : k for k, v in key_to_quest.items() for vv in v}

def find_pattern(query, answer_only_from_model=False):
    query = query.replace('ё', 'е').replace('Ё', 'Е')
    query_for_model = query
    if answer_only_from_model:
        ans_to_ret = searcher.get_answer(query)
        ans_tmp = ans_to_ret.lower()
        tmp_q = [] # to ask question
        for x in query.split():
            x_morph = morph.parse(x)[0]
            if x_morph.tag.POS == "NOUN" and x_morph.tag.animacy == "anim":
                tmp_q.append(x_morph.normal_form)
            else:
                tmp_q.append(x)
        ans_tmp = ' '.join(tmp_q)
        found_name = None
        for name in names_sorted:
            if name in ans_tmp:
                found_name = name
                break
        return ans_to_ret, found_name
    found_name = None
    found_key = None
    query = query.lower()
    tmp_q = []
    for x in query.split():
        x_morph = morph.parse(x)[0]
        if x_morph.tag.POS == "NOUN" and x_morph.tag.animacy == "anim":
            tmp_q.append(x_morph.normal_form)
        else:
            tmp_q.append(x)
    query = ' '.join(tmp_q)
    for name in names_sorted:
        if name in query:
            found_name = name
            break
    for q in quest_to_key.keys():
        if re.search(q, query, re.DOTALL) is not None:
            found_key = quest_to_key[q]
            break
    if found_name is not None:
        if found_key is not None:
            ans_to_ret = name_to_features[found_name][found_key]
            if ans_to_ret != 'nan':
                if found_key == 'death':
                    if str(ans_to_ret) == 'nan':
                        return 'Всё ещё жив !', found_name
                    else:
                        return 'Умер ' + ans_to_ret, found_name
                else:
                    return ans_to_ret, found_name
    ans_to_ret = searcher.get_answer(query_for_model)
    ans_tmp = ans_to_ret.lower()
    tmp_q = [] # to ask question
    for x in query.split():
        x_morph = morph.parse(x)[0]
        if x_morph.tag.POS == "NOUN" and x_morph.tag.animacy == "anim":
            tmp_q.append(x_morph.normal_form)
        else:
            tmp_q.append(x)
    ans_tmp = ' '.join(tmp_q)
    found_name = None
    for name in names_sorted:
        if name in ans_tmp:
            found_name = name
            break
    return ans_to_ret, found_name
            # return name_to_features[name]
    # else:
    #     if found_key is not None:
    #         return f'Увы!\nЯ не нашла у такого {found_key} !'
    #     else:
    #         return 'Увы!\nЯ не нашла такого!'

def ask_question(entity):
    global end_q
    question_list, flag  = get_suggest(entity)
    if flag:
        s = random.choice(question_list) + ' ' +random.choice(end_q) + '?'
    else:
        s = random.choice(question_list) + "?"
    return 'А ' + s

log_dict = {}
user_to_hash = defaultdict(lambda : [])
        
@bot.message_handler(commands=['start', 'help', 'stop'])
def commands_reply(message):
    global log_file
    if message.text == '/start':
        bot.send_message(message.from_user.id, welcome_message)
        bot.register_next_step_handler(message, chatter)
    elif message.text == '/help':
        bot.send_message(message.from_user.id, "Привет!\nЧтобы начать общение напиши /start\nЧтобы закрыть меня -- /stop")
        bot.register_next_step_handler(message, commands_reply)
    elif message.text == '/stop':
        u_id = message.from_user.id
        for hash_id in user_to_hash[u_id]: # clearing log info
            res = log_dict.pop(hash_id, None)
            if res is not None:
                u_id, query, ans, timestamp = res.split('\t')
                d_t = datetime.datetime.fromtimestamp(float(timestamp)).strftime("%d/%m/%Y %H:%M:%S")
                log_file.write('\t'.join([u_id,query,ans,d_t,'unk']) + '\n')
                log_file.flush()
        user_to_hash.pop(u_id, None)
        bot.send_message(message.from_user.id, goodby_message)
#         bot.register_next_step_handler(message, commands_reply)
    else:
        bot.send_message(message.from_user.id, dummy_message)
        bot.register_next_step_handler(message, commands_reply)

@bot.message_handler(content_types=['text'])
def unknown_reply(message):
    bot.send_message(message.from_user.id, unknown_message)
    bot.register_next_step_handler(message, commands_reply)
        
@bot.message_handler(content_types=['text'])
def chatter(message):
    global answers
    global ans_len
    global log_dict
    global find_pattern
    global ask_question
    global quest_to_key
    global name_to_features
    query = message.text
    if query in ['/start', '/help', '/stop']:
        commands_reply(message)
        return
    ans, entity = find_pattern(query, False)
    # print(ans)
    user_id = str(message.from_user.id)
    str_time = str(datetime.datetime.today().timestamp())
    log_info = user_id + '\t' + query + '\t' + ans + '\t' + str_time
    hash_info = hash(log_info)
    log_dict[hash_info] = log_info
    user_to_hash[message.from_user.id].append(hash_info)
    keyboard = types.InlineKeyboardMarkup()
    key_good = types.InlineKeyboardButton(text='Хороший ответ', callback_data=str(hash_info) + '\t' + 'good')
    keyboard.add(key_good)
    key_bad = types.InlineKeyboardButton(text='Плохой ответ', callback_data=str(hash_info) + '\t' + 'bad')
    keyboard.add(key_bad)
    bot.send_message(message.from_user.id, text=ans, reply_markup=keyboard)
    if entity is not None:
        if np.random.randint(0, 100, 1)[0] % 3 == 0:
            gen_q = ask_question(entity)
            bot.send_message(message.from_user.id, text=gen_q)
    bot.register_next_step_handler(message, chatter)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    global log_dict
    global log_file
    hash_info, ans_type = call.data.split('\t')
    hash_info = int(hash_info)
    try:
        u_id, query, ans, timestamp = log_dict[hash_info].split('\t')
    except KeyError:
        print("Already logged this one!")
        return
    d_t = datetime.datetime.fromtimestamp(float(timestamp)).strftime("%d/%m/%Y %H:%M:%S")
    if ans_type == "good":
        log_file.write('\t'.join([u_id,query,ans,d_t,'good']) + '\n')
        log_file.flush()
    elif ans_type == "bad":
        log_file.write('\t'.join([u_id,query,ans,d_t,'bad']) + '\n')
        log_file.flush()
    else:
        raise ValueError("Wrong answer type in callback !!!")
    del log_dict[hash_info]

with open("HP_LOG.txt", mode="a+") as log_file:
    bot.polling(none_stop=True, interval=0)
