import asyncio, random, docx, os, time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# TOKEN
TOKEN = "8758698721:AAHjncKEIOuEOhz3CVvy66zGrjM6wcPA448"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def load_all_questions():
    tests = []
    try:
        path = os.path.join(os.path.dirname(__file__), 'savollar.docx')
        doc = docx.Document(path)
        current = None
        for p in doc.paragraphs:
            t = p.text.strip().replace('\ufeff', '')
            if not t: continue
            if t.startswith('?'):
                if current and current['correct']: tests.append(current)
                current = {'q': t[1:].strip(), 'options': [], 'correct': ''}
            elif t.startswith('+') and current:
                ans = t[1:].strip()
                current['options'].append(ans)
                current['correct'] = ans
            elif t.startswith('=') and current:
                current['options'].append(t[1:].strip())
        if current and current['correct']: tests.append(current)
    except Exception as e:
        print(f"Xato: {e}")
    return tests

all_questions = load_all_questions()
user_exams = {}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Imtihonni boshlash", callback_data="start_exam")
    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
        f"Imtihon **25 ta savoldan** iborat.\n"
        f"Umumiy vaqt: **25 daqiqa**.\n"
        f"Har bir savolga max: 60 soniya.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "start_exam")
async def start_exam_process(callback: types.Callback_query):
    uid = callback.from_user.id
    if len(all_questions) < 25:
        await callback.answer("Savollar yetarli emas!", show_alert=True)
        return

    user_exams[uid] = {
        'qs': random.sample(all_questions, 25), 
        'index': 0, 'score': 0, 
        'msg_id': None, 
        'start_time': time.time(),
        'timer_task': None, 
        'current_options': []
    }
    await callback.message.delete()
    await send_next_question(uid)

async def send_next_question(uid):
    if uid not in user_exams: return
    data = user_exams[uid]
    
    # Umumiy vaqt nazorati (25 minut = 1500 soniya)
    if time.time() - data['start_time'] > 1500:
        await finish_exam(uid, "⏰ Umumiy vaqtingiz tugadi!")
        return

    if data['index'] >= 25:
        await finish_exam(uid, "🎉 Imtihon yakunlandi!")
        return

    q_data = data['qs'][data['index']]
    options = list(q_data['options'])
    random.shuffle(options)
    data['current_options'] = options

    text = f"📝 **Savol {data['index']+1}/25**\n\n{q_data['q']}\n\n"
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        char = chr(65 + i)
        text += f"**{char})** {opt}\n"
        builder.button(text=char, callback_data=f"ans_{i}")
    
    builder.adjust(2)
    try:
        msg = await bot.send_message(uid, text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        data['msg_id'] = msg.message_id
        data['timer_task'] = asyncio.create_task(timer_process(uid, data['index']))
    except:
        # Markdown xatosi bo'lsa oddiy matnda yuborish
        msg = await bot.send_message(uid, text.replace('*', ''), reply_markup=builder.as_markup())
        data['msg_id'] = msg.message_id
        data['timer_task'] = asyncio.create_task(timer_process(uid, data['index']))

async def timer_process(uid, current_idx):
    await asyncio.sleep(60) # Har bir savol uchun 60 soniya kutish
    if uid in user_exams and user_exams[uid]['index'] == current_idx:
        try:
            await bot.delete_message(uid, user_exams[uid]['msg_id'])
        except: pass
        user_exams[uid]['index'] += 1
        await send_next_question(uid)

@dp.callback_query(F.data.startswith("ans_"))
async def handle_answer(callback: types.Callback_query):
    uid = callback.from_user.id
    if uid not in user_exams: return
    
    data = user_exams[uid]
    opt_idx = int(callback.data.split("_")[1]) # Bu yerda split xatosi tuzatildi
    user_ans = data['current_options'][opt_idx]
    current_q = data['qs'][data['index']]

    if data['timer_task']: data['timer_task'].cancel()

    if user_ans.strip() == current_q['correct'].strip():
        await callback.answer("✅ To'g'ri!")
        data['score'] += 1
    else:
        await callback.answer("❌ Noto'g'ri!")

    try: await bot.delete_message(uid, data['msg_id'])
    except: pass
    
    data['index'] += 1
    await send_next_question(uid)

async def finish_exam(uid, reason):
    data = user_exams[uid]
    user = await bot.get_chat(uid)
    score = data['score']
    percent = (score / 25) * 100
    duration = int(time.time() - data['start_time'])
    m, s = divmod(duration, 60)
    
    res = (f"{reason}\n\n"
           f"👤 Foydalanuvchi: **{user.full_name}**\n"
           f"✅ To'g'ri javoblar: **{score} / 25**\n"
           f"📈 Natija: **{percent}%**\n"
           f"⏱ Sarflangan vaqt: **{m} daqiqa {s} soniya**")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Qayta ishlash", callback_data="start_exam")
    await bot.send_message(uid, res, reply_markup=builder.as_markup(), parse_mode="Markdown")
    del user_exams[uid]

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print(f"Bot ishga tushdi! Imtihon vaqti: 25 minut.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
