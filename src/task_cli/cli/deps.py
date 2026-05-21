from task_cli.services.global_config_service import GlobalConfigService
from task_cli.storage.global_config_storage import GlobalConfigStorage
from task_cli.usecases.task_crud_usecase import TaskCrudUseCase


def get_global_config_service() -> GlobalConfigService:
    return GlobalConfigService(GlobalConfigStorage())


def get_use_case() -> TaskCrudUseCase:
    return TaskCrudUseCase(get_global_config_service())
