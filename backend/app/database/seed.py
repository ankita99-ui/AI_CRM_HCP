from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hcp import HCP
from app.models.interaction import ActivityLog, Interaction, InteractionProduct
from app.models.user import User


async def seed_database(session: AsyncSession) -> None:
    existing_user = await session.scalar(select(User).limit(1))
    if existing_user:
        return

    user = User(name='Ava Medical Rep', email='ava.rep@aicrm.local')
    session.add(user)
    await session.flush()

    hcps = [
        HCP(doctor_name='Dr Amit Sharma', hospital='Sunrise Care Hospital', speciality='Endocrinology', city='Mumbai', email='amit.sharma@sunrisecare.org', history_summary='Interested in metabolic therapies and clinical evidence packs.'),
        HCP(doctor_name='Dr Neha Rao', hospital='Lotus Heart Center', speciality='Cardiology', city='Pune', email='neha.rao@lotusheart.org', history_summary='Prefers concise product updates and congress summaries.'),
        HCP(doctor_name='Dr Vikram Patel', hospital='Apollo Specialist Clinic', speciality='Diabetology', city='Bengaluru', email='vikram.patel@apollo-specialist.org', history_summary='Requests outcome data and patient selection guidance.'),
    ]
    session.add_all(hcps)
    await session.flush()

    interaction_1 = Interaction(
        hcp_id=hcps[0].id,
        user_id=user.id,
        interaction_type='visit',
        discussion_notes='Discussed Ozempic and requested latest clinical trial evidence.',
        summary='Reviewed Ozempic positioning and physician requested updated trial data.',
        sentiment='positive',
        follow_up_date=date.today() + timedelta(days=5),
        status='logged',
    )
    interaction_2 = Interaction(
        hcp_id=hcps[1].id,
        user_id=user.id,
        interaction_type='call',
        discussion_notes='Discussed cardiovascular outcomes and conference opportunity.',
        summary='Aligned on cardiovascular evidence and potential event engagement.',
        sentiment='neutral',
        follow_up_date=date.today() + timedelta(days=7),
        status='logged',
    )
    session.add_all([interaction_1, interaction_2])
    await session.flush()

    session.add_all([
        InteractionProduct(interaction_id=interaction_1.id, product_name='Ozempic'),
        InteractionProduct(interaction_id=interaction_1.id, product_name='Rybelsus'),
        InteractionProduct(interaction_id=interaction_2.id, product_name='Jardiance'),
        ActivityLog(interaction_id=interaction_1.id, user_id=user.id, action='seeded_interaction', details='Seeded sample interaction one'),
        ActivityLog(interaction_id=interaction_2.id, user_id=user.id, action='seeded_interaction', details='Seeded sample interaction two'),
    ])
    await session.commit()
