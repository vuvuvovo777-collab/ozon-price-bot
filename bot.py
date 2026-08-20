import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ozon_parser import search_cheapest


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Я ищу товары на Ozon и показываю самые дешёвые предложения.\n\n"
        "Просто напиши, например:\n"
        "☕ кофе 1 кг\n\n"
        "Или:\n"
        "☕ кофе 1 кг до 1500"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


async def search_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if not query:
        return

    wait_message = await update.message.reply_text(
        "🔎 Ищу самые дешёвые предложения на Ozon..."
    )

    try:
        products = await asyncio.to_thread(
            search_cheapest,
            query,
            5
        )

        if not products:
            await wait_message.edit_text(
                "😔 Не удалось найти подходящие товары.\n\n"
                "Попробуй изменить запрос."
            )
            return

        await wait_message.delete()

        for index, product in enumerate(products, start=1):

            title = product.get("title", "Без названия")
            price = product.get("price")
            url = product.get("url")
            image = product.get("image")

            if price is not None:
                price_text = f"{price:,.0f}".replace(",", " ")
            else:
                price_text = "Цена не указана"

            text = (
                f"<b>#{index} — {title}</b>\n\n"
                f"💰 <b>{price_text} ₽</b>\n"
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛒 Открыть на Ozon",
                        url=url
                    )
                ]
            ])

            if image:
                try:
                    await update.message.reply_photo(
                        photo=image,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    continue
                except Exception:
                    pass

            await update.message.reply_text(
                text + f"\n🔗 {url}",
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as error:
        print("ERROR:", error)

        await wait_message.edit_text(
            "⚠️ При поиске произошла ошибка.\n\n"
            "Попробуй ещё раз через несколько секунд."
        )


def main():
    if not TOKEN:
        raise RuntimeError(
            "Не найден TELEGRAM_BOT_TOKEN"
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            search_products
        )
    )

    print("Bot started!")

    app.run_polling()


if __name__ == "__main__":
    main()
