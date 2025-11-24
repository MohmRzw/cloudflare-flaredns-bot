import os
import json
import asyncio
from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from config import BOT_TOKEN, ADMIN_ID, API_URL, ACCOUNTS_FILE, ICONS


dp = Dispatcher()
user_cache: dict[int, dict] = {}  # {user_id: {...}}


# ==================== آیکون پروکسی ====================
def get_proxy_icon(proxied: bool) -> str:
    return ICONS["PROXIED"] if proxied else ICONS["DNS_ONLY"]


# ==================== مدیریت فایل اکانت‌ها ====================
def load_accounts() -> dict:
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                return {
                    item["name"]: item["token"]
                    for item in data
                    if isinstance(item, dict) and "name" in item and "token" in item
                }
            return {}
    except Exception:
        return {}


def save_account(name: str, token: str):
    data = load_accounts()
    data[name] = token
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_account_from_file(name: str):
    data = load_accounts()
    if name in data:
        del data[name]
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def get_active_token(user_id: int) -> str | None:
    cache = user_cache.setdefault(user_id, {})
    active_name = cache.get("active_acc")
    accounts = load_accounts()

    if active_name and active_name in accounts:
        return accounts[active_name]

    if active_name and active_name not in accounts:
        cache["active_acc"] = None

    if len(accounts) == 1:
        only = next(iter(accounts.keys()))
        cache["active_acc"] = only
        return accounts[only]

    return None


# ==================== FSM ====================
class AccountForm(StatesGroup):
    name = State()
    token = State()


class RecordForm(StatesGroup):
    type = State()
    name = State()
    content = State()
    ttl = State()
    proxied = State()


class EditField(StatesGroup):
    value = State()   # ویرایش تک‌فیلدی رکورد (نام/مقدار/TTL)


# ==================== UI کمکی ====================
def header(title: str, user_id: int | None = None) -> str:
    if user_id is not None:
        acc_name = user_cache.get(user_id, {}).get("active_acc") or "انتخاب نشده"
    else:
        acc_name = "..."
    return (
        f"<b>☁️ Cloudflare Manager | {title}</b>\n"
        f"👤 اکانت فعال: <code>{acc_name}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
    )


def back_btn(target: str = "home", refresh: str | None = None):
    kb = InlineKeyboardBuilder()
    if refresh:
        kb.button(text=f"{ICONS['REFRESH']} بروزرسانی", callback_data=refresh)
    kb.button(text=f"{ICONS['BACK']} بازگشت", callback_data=target)
    return kb.as_markup()


def get_main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['ZONES']} دامنه‌های من", callback_data="zones_list")
    kb.button(text=f"{ICONS['ACCOUNTS']} مدیریت اکانت‌ها", callback_data="acc_manage")
    kb.button(text=f"{ICONS['STATS']} آمار پیشرفته", callback_data="global_stats")
    kb.button(text=f"{ICONS['HELP']} راهنما", callback_data="help")
    kb.button(text=f"{ICONS['LOGOUT']} خروج / تغییر اکانت", callback_data="logout_action")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# ==================== Cloudflare API ====================
async def cf_request(user_id: int, method: str, endpoint: str, data: dict | None = None):
    token = get_active_token(user_id)
    if not token:
        raise Exception("NO_ACCOUNT_SELECTED")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with ClientSession() as s:
        async with s.request(method, API_URL + endpoint, headers=headers, json=data, timeout=25) as r:
            j = await r.json()
            if not j.get("success"):
                msgs = [e.get("message") for e in j.get("errors", [])]
                raise Exception("\n".join(msgs) or "Cloudflare error")
            return j["result"]


# ==================== /start ====================
@dp.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID:
        return

    await state.clear()
    user_cache.setdefault(m.from_user.id, {})

    accounts = load_accounts()
    if not accounts:
        kb = InlineKeyboardBuilder()
        kb.button(text=f"{ICONS['ADD']} افزودن اولین اکانت", callback_data="acc_add")
        kb.button(text="🎓 آموزش دریافت توکن", callback_data="tutorial")
        kb.adjust(1)
        await m.answer(
            "👋 <b>سلام مدیر!</b>\n\n"
            "هنوز هیچ اکانت کلودفلری اضافه نشده است.\n"
            "برای شروع، باید یک توکن اضافه کنید.",
            reply_markup=kb.as_markup(),
        )
    else:
        _ = get_active_token(m.from_user.id)
        await m.answer(
            header("داشبورد", m.from_user.id) + "به پنل مدیریت خوش آمدید.",
            reply_markup=get_main_menu(),
        )


@dp.callback_query(F.data == "home")
async def go_home(cb: CallbackQuery, state: FSMContext | None = None):
    if state:
        await state.clear()
    text = header("منوی اصلی", cb.from_user.id) + "یک گزینه را انتخاب کنید:"
    try:
        await cb.message.edit_text(text, reply_markup=get_main_menu())
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await cb.answer()
        else:
            raise


# ==================== Logout ====================
@dp.callback_query(F.data == "logout_action")
async def logout_process(cb: CallbackQuery):
    user_cache.setdefault(cb.from_user.id, {})["active_acc"] = None
    await cb.answer("از اکانت فعلی خارج شدید.", show_alert=False)
    await accounts_menu(cb)


# ==================== Help ====================
@dp.callback_query(F.data == "help")
async def help_menu(cb: CallbackQuery):
    text = (
        "<b>ℹ️ راهنمای استفاده از ربات</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"<b>{ICONS['ZONES']} دامنه‌های من:</b>\n"
        "لیست دامنه‌های متصل به اکانت فعال را می‌بینید.\n\n"
        f"<b>{ICONS['ACCOUNTS']} مدیریت اکانت‌ها:</b>\n"
        "اکانت‌های مختلف Cloudflare را اضافه/حذف و بین آن‌ها جابه‌جا کنید.\n\n"
        f"<b>{ICONS['STATS']} آمار پیشرفته:</b>\n"
        "نمای کلی تعداد دامنه‌ها، فعال و در انتظار.\n\n"
        f"<b>{ICONS['LOGOUT']} خروج / تغییر اکانت:</b>\n"
        "برای خارج شدن از اکانت فعلی و انتخاب حساب دیگر."
    )
    await cb.message.edit_text(header("راهنما", cb.from_user.id) + text, reply_markup=back_btn())


# ==================== Tutorial ====================
@dp.callback_query(F.data == "tutorial")
async def show_tutorial(cb: CallbackQuery):
    text = (
        "<b>🎓 آموزش دریافت توکن Cloudflare (API Token)</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ وارد <a href='https://dash.cloudflare.com'>Cloudflare.com</a> شوید.\n"
        "2️⃣ My Profile → API Tokens → Create Token\n"
        "3️⃣ قالب Edit zone DNS را Use template کنید.\n"
        "4️⃣ Zone Resources را روی All zones بگذارید.\n"
        "5️⃣ Continue to summary → Create Token\n"
        "6️⃣ توکن را کپی کنید و در ربات وارد کنید."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['ADD']} افزودن اکانت", callback_data="acc_add")
    kb.button(text=f"{ICONS['BACK']} منوی اصلی", callback_data="home")
    kb.adjust(1)
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), disable_web_page_preview=True)


# ==================== مدیریت اکانت‌ها ====================
@dp.callback_query(F.data == "acc_manage")
async def accounts_menu(cb: CallbackQuery):
    user_id = cb.from_user.id
    _ = get_active_token(user_id)

    accounts = load_accounts()
    active = user_cache.get(user_id, {}).get("active_acc")

    kb = InlineKeyboardBuilder()
    cache = user_cache.setdefault(user_id, {})

    if not accounts:
        msg = f"{ICONS['WARNING']} لیست اکانت‌ها خالی است."
        cache["acc_index_map"] = {}
    else:
        msg = (
            f"{ICONS['ACCOUNTS']} <b>لیست حساب‌های متصل شده:</b>\n"
            "روی نام برای ورود، روی حذف برای پاک‌کردن کلیک کنید:\n"
        )
        acc_names = list(accounts.keys())
        cache["acc_index_map"] = {str(i): name for i, name in enumerate(acc_names)}

        for i, name in enumerate(acc_names):
            idx = str(i)
            status_icon = "🔵" if name == active else "⚪️"
            kb.button(text=f"{status_icon} {name}", callback_data=f"accsel#{idx}")
            kb.button(text=f"{ICONS['DELETE']} حذف", callback_data=f"accdel#{idx}")
        kb.adjust(2)

    kb.row(InlineKeyboardButton(text=f"{ICONS['ADD']} افزودن اکانت جدید", callback_data="acc_add"))
    kb.row(InlineKeyboardButton(text=f"{ICONS['BACK']} بازگشت به خانه", callback_data="home"))

    text = header("مدیریت حساب‌ها", user_id) + msg
    markup = kb.as_markup()
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await cb.answer()
        else:
            raise


# --- افزودن اکانت ---
@dp.callback_query(F.data == "acc_add")
async def acc_add_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AccountForm.name)
    await cb.message.edit_text(
        "✍️ <b>نام اکانت را وارد کنید:</b>\nمثال: شخصی، شرکت، مشتری 1",
        reply_markup=back_btn("acc_manage"),
    )


@dp.message(AccountForm.name)
async def acc_add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(AccountForm.token)

    kb = InlineKeyboardBuilder()
    kb.button(text="🎓 آموزش دریافت توکن", callback_data="tutorial")
    kb.button(text=f"{ICONS['CANCEL']} انصراف", callback_data="acc_manage")
    kb.adjust(1, 1)

    await m.answer(
        f"{ICONS['KEY']} <b>حالا API Token را ارسال کنید:</b>\n"
        "اگر نمی‌دانید از کجا توکن بگیرید، روی «آموزش دریافت توکن» بزنید.",
        reply_markup=kb.as_markup()
    )


@dp.message(AccountForm.token)
async def acc_add_token(m: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    token = m.text.strip()
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with ClientSession() as s:
            async with s.get(API_URL + "/user/tokens/verify", headers=headers) as r:
                j = await r.json()
                if not j.get("success") or j.get("result", {}).get("status") != "active":
                    raise Exception("Invalid Token")
        save_account(name, token)
        user_cache.setdefault(m.from_user.id, {})["active_acc"] = name
        await state.clear()
        await m.answer(
            f"{ICONS['SUCCESS']} اکانت <b>{name}</b> با موفقیت اضافه و فعال شد.",
            reply_markup=get_main_menu(),
        )
    except Exception:
        await m.answer(
            f"{ICONS['ERROR']} <b>توکن نامعتبر است!</b>\n"
            "مطمئن شوید توکن درست کپی شده و دوباره ارسال کنید."
        )


# --- انتخاب اکانت بر اساس index ---
@dp.callback_query(F.data.startswith("accsel#"))
async def acc_select(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    idx = cb.data.split("#", 1)[1]
    cache = user_cache.setdefault(user_id, {})
    name = cache.get("acc_index_map", {}).get(idx)

    if not name:
        return await cb.answer("اکانت پیدا نشد، منو را رفرش کنید.", show_alert=True)

    # اگر همین اکانت الان فعال است، فقط پیام بده و صفحه را دست نزن
    if cache.get("active_acc") == name:
        return await cb.answer("این اکانت در حال حاضر فعال است.", show_alert=False)

    cache["active_acc"] = name
    await state.clear()
    await cb.answer(f"اکانت «{name}» فعال شد {ICONS['SUCCESS']}", show_alert=False)
    await accounts_menu(cb)


# --- حذف اکانت: مرحله سؤال ---
@dp.callback_query(F.data.startswith("accdel#"))
async def acc_delete_ask(cb: CallbackQuery):
    user_id = cb.from_user.id
    idx = cb.data.split("#", 1)[1]
    cache = user_cache.setdefault(user_id, {})
    name = cache.get("acc_index_map", {}).get(idx)

    if not name:
        return await cb.answer("اکانت پیدا نشد، منو را رفرش کنید.", show_alert=True)

    kb = InlineKeyboardBuilder()
    kb.button(
        text=f"{ICONS['CONFIRM']} بله، حذف کن",
        callback_data=f"accdelc#{idx}",
    )
    kb.button(
        text=f"{ICONS['CANCEL']} انصراف",
        callback_data="acc_manage",
    )
    kb.adjust(2)

    await cb.message.edit_text(
        header("حذف اکانت", user_id)
        + f"⚠️ آیا از حذف اکانت «<b>{name}</b>» مطمئن هستید؟",
        reply_markup=kb.as_markup(),
    )


# --- حذف اکانت: مرحله تأیید ---
@dp.callback_query(F.data.startswith("accdelc#"))
async def acc_delete_confirm(cb: CallbackQuery):
    user_id = cb.from_user.id
    idx = cb.data.split("#", 1)[1]
    cache = user_cache.setdefault(user_id, {})
    name = cache.get("acc_index_map", {}).get(idx)

    if not name:
        return await cb.answer("اکانت پیدا نشد، منو را رفرش کنید.", show_alert=True)

    delete_account_from_file(name)

    if cache.get("active_acc") == name:
        accounts = load_accounts()
        if len(accounts) == 1:
            cache["active_acc"] = next(iter(accounts.keys()))
        elif accounts:
            cache["active_acc"] = None
        else:
            cache["active_acc"] = None

    await cb.answer(f"اکانت «{name}» حذف شد.", show_alert=False)
    await accounts_menu(cb)


# ==================== آمار پیشرفته ====================
@dp.callback_query(F.data == "global_stats")
async def global_stats(cb: CallbackQuery):
    accounts = load_accounts()
    if not accounts:
        return await cb.answer("هیچ اکانتی وجود ندارد.", show_alert=True)

    await cb.message.edit_text(f"{ICONS['SPINNER']} در حال دریافت اطلاعات...")

    report = ""
    total_zones = 0
    total_active = 0
    total_pending = 0
    acc_count = 0

    for name, token in accounts.items():
        acc_count += 1
        try:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with ClientSession() as s:
                async with s.get(API_URL + "/zones?per_page=50", headers=headers) as r:
                    res = await r.json()
                    if res.get("success"):
                        zones = res["result"]
                        count = len(zones)
                        active_z = sum(1 for z in zones if z["status"] == "active")
                        pending_z = count - active_z

                        total_zones += count
                        total_active += active_z
                        total_pending += pending_z

                        report += (
                            f"🔹 <b>{name}:</b>\n"
                            f"   ├ کل دامنه‌ها: {count}\n"
                            f"   ├ {ICONS['ACTIVE']} فعال: {active_z}\n"
                            f"   └ {ICONS['PENDING']} در انتظار: {pending_z}\n\n"
                        )
                    else:
                        report += f"🔹 <b>{name}:</b> {ICONS['ERROR']} توکن منقضی/نامعتبر\n\n"
        except Exception:
            report += f"🔹 <b>{name}:</b> {ICONS['ERROR']} خطا در اتصال\n\n"

    txt = (
        header("گزارش جامع", cb.from_user.id)
        + f"📈 <b>خلاصه وضعیت:</b>\n"
        f"👥 تعداد اکانت‌ها: {acc_count}\n"
        f"🌍 مجموع دامنه‌ها: {total_zones}\n"
        f"{ICONS['ACTIVE']} مجموع فعال: {total_active}\n"
        f"{ICONS['WARNING']} مجموع در انتظار: {total_pending}\n"
        "━━━━━━━━━━━━━━━━\n"
        + report
    )
    await cb.message.edit_text(txt, reply_markup=back_btn())


# ==================== لیست دامنه‌ها ====================
@dp.callback_query(F.data == "zones_list")
async def list_zones_start(cb: CallbackQuery):
    try:
        zones = await cf_request(cb.from_user.id, "GET", "/zones?per_page=50")
        user_cache.setdefault(cb.from_user.id, {})["zones"] = zones
        await render_zones_page(cb, 0)
    except Exception as e:
        if "NO_ACCOUNT_SELECTED" in str(e):
            await cb.message.edit_text(
                "⚠️ هنوز اکانتی انتخاب نکرده‌اید.\nلطفاً یک اکانت را انتخاب کنید:",
                reply_markup=back_btn("acc_manage"),
            )
        else:
            await cb.message.edit_text(f"{ICONS['ERROR']} خطا: {e}", reply_markup=back_btn())


async def render_zones_page(cb: CallbackQuery, page: int):
    zones = user_cache.get(cb.from_user.id, {}).get("zones", [])
    if not zones:
        return await cb.message.edit_text(
            header("دامنه‌ها", cb.from_user.id) + "❌ هیچ دامنه‌ای در این اکانت یافت نشد.",
            reply_markup=back_btn(),
        )

    per_page = 6
    max_page = (len(zones) - 1) // per_page
    start = page * per_page
    end = start + per_page
    slice_z = zones[start:end]

    kb = InlineKeyboardBuilder()
    for z in slice_z:
        status_icon = "🟢" if z["status"] == "active" else "🟠"
        kb.button(text=f"{status_icon} {z['name']}", callback_data=f"zone_{z['id']}")
    kb.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"zpage_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max_page+1}", callback_data="noop"))
    if end < len(zones):
        nav.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"zpage_{page+1}"))
    if nav:
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text=f"{ICONS['BACK']} منوی اصلی", callback_data="home"))

    await cb.message.edit_text(
        header("انتخاب دامنه", cb.from_user.id) + "دامنه مورد نظر را انتخاب کنید:",
        reply_markup=kb.as_markup(),
    )


@dp.callback_query(F.data.startswith("zpage_"))
async def zone_pagination(cb: CallbackQuery):
    page = int(cb.data.split("_")[1])
    await render_zones_page(cb, page)


# ==================== لیست رکوردهای DNS ====================
@dp.callback_query(F.data.startswith("zone_"))
async def list_records(cb: CallbackQuery):
    zone_id = cb.data.split("_")[1]
    uid = cb.from_user.id

    zones = user_cache.get(uid, {}).get("zones", [])
    zobj = next((z for z in zones if z["id"] == zone_id), None)
    zone_name = zobj["name"] if zobj else "Unknown"

    cache = user_cache.setdefault(uid, {})
    cache["curr_zone_id"] = zone_id
    cache["curr_zone_name"] = zone_name

    msg = await cb.message.edit_text(f"{ICONS['SPINNER']} دریافت رکوردهای {zone_name}...")

    try:
        records = await cf_request(uid, "GET", f"/zones/{zone_id}/dns_records?per_page=100")
        cache["records"] = records

        kb = InlineKeyboardBuilder()
        kb.button(text=f"{ICONS['ADD']} ثبت رکورد جدید", callback_data="new_rec_type")

        for r in records:
            proxy_icon = get_proxy_icon(r.get("proxied"))
            type_icon = ICONS.get(r["type"], ICONS["DEFAULT"])
            clean_name = r["name"].replace(f".{zone_name}", "").replace(zone_name, "@") or "@"
            val_short = (r["content"][:15] + "..") if len(r["content"]) > 15 else r["content"]
            kb.button(text=f"{type_icon} {clean_name} ➜ {val_short} {proxy_icon}", callback_data=f"rec_{r['id']}")

        kb.adjust(1)
        kb.row(InlineKeyboardButton(text=f"{ICONS['REFRESH']} رفرش لیست", callback_data=f"zone_{zone_id}"))
        kb.row(InlineKeyboardButton(text=f"{ICONS['BACK']} لیست دامنه‌ها", callback_data="zones_list"))

        await msg.edit_text(
            header(f"مدیریت {zone_name}", uid)
            + f"تعداد رکوردها: {len(records)}\nبرای ویرایش روی رکورد کلیک کنید.",
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        await msg.edit_text(f"{ICONS['ERROR']} خطا: {e}", reply_markup=back_btn("zones_list"))


# ==================== افزودن رکورد ====================
@dp.callback_query(F.data == "new_rec_type")
async def add_step1_type(cb: CallbackQuery, state: FSMContext):
    await state.set_state(RecordForm.type)
    kb = InlineKeyboardBuilder()
    for t in ["A", "AAAA", "CNAME", "TXT", "MX", "NS"]:
        kb.button(text=f"{ICONS.get(t, ICONS['TYPE'])} {t}", callback_data=f"settype_{t}")
    kb.adjust(3)
    kb.row(
        InlineKeyboardButton(
            text=f"{ICONS['CANCEL']} لغو",
            callback_data=f"zone_{user_cache[cb.from_user.id]['curr_zone_id']}",
        )
    )
    await cb.message.edit_text("1️⃣ <b>نوع رکورد</b> را انتخاب کنید:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("settype_"))
async def add_step2_name(cb: CallbackQuery, state: FSMContext):
    rtype = cb.data.split("_")[1]
    await state.update_data(type=rtype)
    await state.set_state(RecordForm.name)
    await cb.message.edit_text(
        f"{ICONS['TYPE']} نوع: <b>{rtype}</b>\n\n"
        "2️⃣ <b>نام رکورد</b> را وارد کنید:\n"
        "برای ریشه دامنه از <code>@</code> استفاده کنید.",
        reply_markup=None,
    )


@dp.message(RecordForm.name)
async def add_step3_content(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(RecordForm.content)
    await m.answer("3️⃣ <b>مقدار (Target/IP)</b> را وارد کنید:\nمثال: <code>192.168.1.1</code>")


@dp.message(RecordForm.content)
async def add_step4_ttl(m: Message, state: FSMContext):
    await state.update_data(content=m.text.strip())
    await state.set_state(RecordForm.ttl)
    await m.answer("4️⃣ مقدار <b>TTL</b> را وارد کنید:\n(عدد 1 برای اتوماتیک)")


@dp.message(RecordForm.ttl)
async def add_step5_proxy(m: Message, state: FSMContext):
    ttl = 1
    if m.text.isdigit():
        ttl = int(m.text)
    await state.update_data(ttl=ttl)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['PROXIED']} روشن (Proxied)", callback_data="setproxy_true")
    kb.button(text=f"{ICONS['DNS_ONLY']} خاموش (DNS Only)", callback_data="setproxy_false")
    await state.set_state(RecordForm.proxied)
    await m.answer("5️⃣ وضعیت <b>پروکسی (CDN)</b>:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("setproxy_"))
async def add_step6_finish(cb: CallbackQuery, state: FSMContext):
    proxied = "true" in cb.data
    data = await state.get_data()
    await state.clear()

    zid = user_cache[cb.from_user.id]["curr_zone_id"]

    await cb.message.edit_text(f"{ICONS['SPINNER']} در حال ارسال به کلودفلر...")

    payload = {
        "type": data["type"],
        "name": data["name"],
        "content": data["content"],
        "ttl": data["ttl"],
        "proxied": proxied,
    }

    try:
        await cf_request(cb.from_user.id, "POST", f"/zones/{zid}/dns_records", payload)
        kb = InlineKeyboardBuilder()
        kb.button(text=f"{ICONS['BACK']} بازگشت به لیست", callback_data=f"zone_{zid}")
        kb.adjust(1)
        await cb.message.edit_text(
            f"{ICONS['SUCCESS']} <b>رکورد با موفقیت ساخته شد!</b>",
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        await cb.message.edit_text(
            f"{ICONS['ERROR']} خطا در ساخت رکورد:\n{e}",
            reply_markup=back_btn(f"zone_{zid}"),
        )


# ==================== جزئیات رکورد + ویرایش دکمه‌ای ====================
@dp.callback_query(F.data.startswith("rec_"))
async def show_record_details(cb: CallbackQuery, state: FSMContext):
    await state.clear()

    rid = cb.data.split("_", 1)[1]
    uid = cb.from_user.id

    records = user_cache.get(uid, {}).get("records", [])
    rec = next((r for r in records if r["id"] == rid), None)
    if not rec:
        return await cb.answer("رکورد در حافظه پیدا نشد، لیست را رفرش کنید.", show_alert=True)

    zid = user_cache[uid]["curr_zone_id"]

    proxy_st = (
        f"{ICONS['ACTIVE']} فعال (Proxied)"
        if rec.get("proxied")
        else f"{ICONS['DNS_ONLY']} غیرفعال (DNS Only)"
    )

    text = (
        "<b>📋 جزئیات رکورد</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{ICONS['TYPE']} نوع: <b>{rec['type']}</b>\n"
        f"{ICONS['NAME']} نام: <code>{rec['name']}</code>\n"
        f"{ICONS['TARGET']} مقدار: <code>{rec['content']}</code>\n"
        f"🛡 پروکسی: {proxy_st}\n"
        f"{ICONS['TTL']} TTL: {rec['ttl']}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['EDIT']} تغییر نام", callback_data=f"editf_name_{rid}")
    kb.button(text=f"{ICONS['EDIT']} تغییر مقدار", callback_data=f"editf_content_{rid}")
    kb.button(text=f"{ICONS['EDIT']} تغییر TTL", callback_data=f"editf_ttl_{rid}")
    kb.button(text=f"{ICONS['EDIT']} تغییر پروکسی", callback_data=f"editproxy_{rid}")
    kb.button(text=f"{ICONS['DELETE']} حذف رکورد", callback_data=f"del_ask_{rid}")
    kb.button(text=f"{ICONS['BACK']} بازگشت", callback_data=f"zone_{zid}")
    kb.adjust(2, 2, 1, 1)

    await cb.message.edit_text(text, reply_markup=kb.as_markup())


# --- ویرایش تک‌فیلدی (نام / مقدار / TTL) ---
@dp.callback_query(F.data.startswith("editf_"))
async def edit_field_start(cb: CallbackQuery, state: FSMContext):
    _, field, rid = cb.data.split("_", 2)
    uid = cb.from_user.id

    records = user_cache.get(uid, {}).get("records", [])
    rec = next((r for r in records if r["id"] == rid), None)
    if not rec:
        return await cb.answer("رکورد در حافظه پیدا نشد، لیست را رفرش کنید.", show_alert=True)

    zid = user_cache[uid]["curr_zone_id"]

    await state.set_state(EditField.value)
    await state.update_data(field=field, rid=rid, zid=zid, old=rec)

    if field == "name":
        prompt = (
            f"نام فعلی: <code>{rec['name']}</code>\n"
            "نام جدید را ارسال کنید:"
        )
    elif field == "content":
        prompt = (
            f"مقدار فعلی: <code>{rec['content']}</code>\n"
            "مقدار جدید را ارسال کنید:"
        )
    elif field == "ttl":
        prompt = (
            f"TTL فعلی: <code>{rec['ttl']}</code>\n"
            "TTL جدید را به صورت عدد (مثلاً 1 برای اتوماتیک) ارسال کنید:"
        )
    else:
        return await cb.answer("فیلد ناشناخته.", show_alert=True)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['CANCEL']} انصراف", callback_data=f"rec_{rid}")
    kb.adjust(1)

    await cb.message.edit_text(prompt, reply_markup=kb.as_markup())


@dp.message(EditField.value)
async def edit_field_apply(m: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    rid = data["rid"]
    zid = data["zid"]
    old = data["old"]
    uid = m.from_user.id

    new_val = m.text.strip()
    if not new_val:
        return await m.answer("مقدار خالی است، دوباره ارسال کنید.")

    payload = {
        "type": old["type"],
        "name": old["name"],
        "content": old["content"],
        "ttl": old["ttl"],
        "proxied": old.get("proxied", False),
    }

    if field == "name":
        payload["name"] = new_val
    elif field == "content":
        payload["content"] = new_val
    elif field == "ttl":
        if not new_val.isdigit():
            return await m.answer("TTL باید یک عدد باشد. دوباره ارسال کنید.")
        payload["ttl"] = int(new_val)
    else:
        await state.clear()
        return await m.answer("فیلد ناشناخته.")

    await state.clear()
    await m.answer(f"{ICONS['SPINNER']} در حال اعمال تغییر...")

    try:
        updated = await cf_request(uid, "PUT", f"/zones/{zid}/dns_records/{rid}", payload)

        records = user_cache.get(uid, {}).get("records", [])
        for i, r in enumerate(records):
            if r["id"] == rid:
                records[i] = updated
                break

        kb = InlineKeyboardBuilder()
        kb.button(text=f"{ICONS['BACK']} بازگشت به جزئیات رکورد", callback_data=f"rec_{rid}")
        kb.adjust(1)
        await m.answer(
            f"{ICONS['SUCCESS']} تغییر با موفقیت انجام شد.",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await m.answer(f"{ICONS['ERROR']} خطا در ویرایش: {e}")


# --- ویرایش فقط پروکسی ---
@dp.callback_query(F.data.startswith("editproxy_"))
async def edit_proxy_menu(cb: CallbackQuery):
    rid = cb.data.split("_", 1)[1]
    uid = cb.from_user.id

    records = user_cache.get(uid, {}).get("records", [])
    rec = next((r for r in records if r["id"] == rid), None)
    if not rec:
        return await cb.answer("رکورد در حافظه پیدا نشد، لیست را رفرش کنید.", show_alert=True)

    current = rec.get("proxied", False)
    curr_txt = (
        f"{ICONS['ACTIVE']} فعال (Proxied)" if current else f"{ICONS['DNS_ONLY']} غیرفعال (DNS Only)"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['PROXIED']} روشن (Proxied)", callback_data=f"setproxyrec_true_{rid}")
    kb.button(text=f"{ICONS['DNS_ONLY']} خاموش (DNS Only)", callback_data=f"setproxyrec_false_{rid}")
    kb.button(text=f"{ICONS['BACK']} بازگشت", callback_data=f"rec_{rid}")
    kb.adjust(2, 1)

    await cb.message.edit_text(
        f"وضعیت فعلی پروکسی: {curr_txt}\n"
        "وضعیت جدید را انتخاب کنید:",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data.startswith("setproxyrec_"))
async def edit_proxy_apply(cb: CallbackQuery):
    _, val, rid = cb.data.split("_", 2)
    proxied = (val == "true")
    uid = cb.from_user.id

    records = user_cache.get(uid, {}).get("records", [])
    rec = next((r for r in records if r["id"] == rid), None)
    if not rec:
        return await cb.answer("رکورد در حافظه پیدا نشد، لیست را رفرش کنید.", show_alert=True)

    zid = user_cache[uid]["curr_zone_id"]

    payload = {
        "type": rec["type"],
        "name": rec["name"],
        "content": rec["content"],
        "ttl": rec["ttl"],
        "proxied": proxied,
    }

    await cb.message.edit_text(f"{ICONS['SPINNER']} در حال اعمال تغییر پروکسی...")

    try:
        updated = await cf_request(uid, "PUT", f"/zones/{zid}/dns_records/{rid}", payload)

        for i, r in enumerate(records):
            if r["id"] == rid:
                records[i] = updated
                break

        await cb.message.edit_text(
            f"{ICONS['SUCCESS']} پروکسی با موفقیت تغییر کرد.",
            reply_markup=back_btn(f"rec_{rid}")
        )
    except Exception as e:
        await cb.message.edit_text(
            f"{ICONS['ERROR']} خطا در تغییر پروکسی: {e}",
            reply_markup=back_btn(f"rec_{rid}")
        )


# --- حذف رکورد ---
@dp.callback_query(F.data.startswith("del_ask_"))
async def delete_ask(cb: CallbackQuery):
    rid = cb.data.split("_", 2)[2]
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{ICONS['CONFIRM']} بله، حذف کن", callback_data=f"del_confirm_{rid}")
    kb.button(text=f"{ICONS['CANCEL']} خیر", callback_data=f"rec_{rid}")
    kb.adjust(2)
    await cb.message.edit_text("⚠️ <b>آیا از حذف این رکورد مطمئن هستید؟</b>", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("del_confirm_"))
async def delete_confirm(cb: CallbackQuery):
    rid = cb.data.split("_", 2)[2]
    zid = user_cache[cb.from_user.id]["curr_zone_id"]
    try:
        await cf_request(cb.from_user.id, "DELETE", f"/zones/{zid}/dns_records/{rid}")
        await cb.message.edit_text(
            f"{ICONS['DELETE']} رکورد با موفقیت حذف شد.",
            reply_markup=back_btn(f"zone_{zid}"),
        )
    except Exception as e:
        await cb.message.edit_text(
            f"{ICONS['ERROR']} خطا: {e}",
            reply_markup=back_btn(f"zone_{zid}"),
        )


# ==================== Main ====================
async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    print("🟢 Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
