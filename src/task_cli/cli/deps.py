from task_cli.services.global_config_service import GlobalConfigService
from task_cli.services.timer_service import TimerService
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_cli.usecases.task_crud_usecase import TaskCrudUseCase
from task_cli.usecases.time_tracking_usecase import TimeTrackingUseCase


def get_global_config_service() -> GlobalConfigService:
    return GlobalConfigService(GlobalConfigStorage())


def get_use_case() -> TaskCrudUseCase:
    config_service = get_global_config_service()
    return TaskCrudUseCase(
        config_service,
        time_tracking=TimeTrackingUseCase(config_service, get_timer_service()),
    )


def get_timer_service() -> TimerService:
    return TimerService()


def get_time_tracking_use_case() -> TimeTrackingUseCase:
    return TimeTrackingUseCase(get_global_config_service(), get_timer_service())
