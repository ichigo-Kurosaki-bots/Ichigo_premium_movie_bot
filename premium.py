from config import (
    FREE_REQUESTS,
    PREMIUM_PLANS
)


# ============================================================
# CHECK WHETHER USER CAN REQUEST A MOVIE
# ============================================================

def can_use_movie(user):

    if not user:
        return False

    remaining = int(
        user.get(
            "remaining_requests",
            0
        )
    )

    return remaining > 0


# ============================================================
# GET PREMIUM PLAN BY PRICE
# ============================================================

def get_plan_by_amount(amount):

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return None

    return PREMIUM_PLANS.get(
        amount
    )


# ============================================================
# GET ALL PREMIUM PLANS
# ============================================================

def get_all_plans():

    return PREMIUM_PLANS


# ============================================================
# PLAN TEXT
# ============================================================

def get_plan_text(
    amount,
    plan
):

    return (
        f"💎 <b>{plan['name']}</b>\n\n"
        f"💰 Price: <b>₹{amount}</b>\n"
        f"🎬 Movie requests: "
        f"<b>{plan['requests']}</b>"
    )


# ============================================================
# USER PLAN TEXT
# ============================================================

def get_user_plan_text(user):

    if not user:
        return (
            "❌ User account not found."
        )

    if not user.get(
        "premium",
        False
    ):

        remaining = user.get(
            "remaining_requests",
            FREE_REQUESTS
        )

        return (
            "🆓 <b>Free Plan</b>\n\n"
            f"🎬 Remaining requests: "
            f"<b>{remaining}</b>"
        )

    plan = user.get(
        "plan"
    )

    amount = user.get(
        "paid_amount",
        0
    )

    remaining = user.get(
        "remaining_requests",
        0
    )

    total = user.get(
        "premium_requests",
        0
    )

    return (
        "💎 <b>Premium Account</b>\n\n"
        f"📦 Plan: <b>{plan or 'Premium'}</b>\n"
        f"💰 Paid: <b>₹{amount}</b>\n"
        f"🎬 Total requests: <b>{total}</b>\n"
        f"🎟 Remaining: <b>{remaining}</b>"
    )


# ============================================================
# FORMAT PREMIUM PLANS
# ============================================================

def format_plans():

    lines = [
        "💎 <b>Premium Plans</b>",
        "",
        "Choose a plan:",
        ""
    ]

    for amount, plan in PREMIUM_PLANS.items():

        lines.append(
            f"💰 <b>₹{amount}</b> "
            f"— {plan['requests']} movies"
        )

    lines.extend([
        "",
        "🆓 Free users get 5 movie requests.",
        "",
        "After your free requests are finished, "
        "choose a Premium plan."
    ])

    return "\n".join(
        lines
    )
