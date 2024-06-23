"""
    scheduler = AsyncIOScheduler()
    if len(scheduler.get_jobs()) == 0:  # Думал сперва хранить таски через SQLAlchemyJobStore
        scheduler.add_job(weekly_management_schedule, trigger='cron', day_of_week=6, hour=1,
                          id='schedule_weekly_updates')
    scheduler.start()

    или в новой версии (не стоит):
        data_store = SQLAlchemyDataStore(engine=engine)
        async with AsyncScheduler() as scheduler:
            if len(await scheduler.get_schedules()) == 0:
                await scheduler.add_schedule(weekly_management_schedule,
                                             CronTrigger(day_of_week=6, hour=1),
                                             id="schedule_weekly_updates")
                await scheduler.start_in_background()
    """