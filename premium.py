from config import (
    PREMIUM_PLANS,
    FREE_REQUESTS
)


def get_plan_by_amount(amount):

    return PREMIUM_PLANS.get(
        amount
    )


def get_plan_text():

    text = "💎 <b>Premium Plans</b>\n\n"

    text += (
        "Free Plan → "
        f"{FREE_REQUESTS} requests\n\n"
    )

    for amount, plan in PREMIUM_PLANS.items():

        text += (
            f"💰 ₹{amount} → "
            f"<b>{plan['name']}</b>\n"
            f"🎬 {plan['requests']} movie requests\n\n"
        )

    text += (
        "💳 After payment, contact the owner "
        "with your Telegram ID."
    )

    return text


def get_user_plan_text(user):

    if not user:
        return "User not found."

    premium = user.get(
        "premium",
        False
    )

    remaining = user.get(
        "remaining_requests",
        0
    )

    used = user.get(
        "used_requests",
        0
    )

    if premium:

        plan = user.get(
            "plan",
            "Premium"
        )

        amount = user.get(
            "paid_amount",
            0
        )

        return (
            "💎 <b>Premium Account</b>\n\n"
            f"📦 Plan: <b>{plan}</b>\n"
            f"💰 Paid: ₹{amount}\n"
            f"🎬 Used: {used}\n"
            f"🎬 Remaining: <b>{remaining}</b>"
        )

    return (
        "🆓 <b>Free Account</b>\n\n"
        f"🎬 Used: {used}\n"
        f"🎬 Remaining: <b>{remaining}</b>\n\n"
        "Upgrade to Premium when your "
        "free requests are finished."
    )


def can_use_movie(user):

    if not user:
        return False

    return user.get(
        "remaining_requests",
        0
    ) > 0
