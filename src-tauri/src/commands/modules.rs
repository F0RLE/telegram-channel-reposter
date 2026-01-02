use crate::domain::modules::models::{ControlRequest, ControlResponse, ModuleItem};
use crate::domain::modules::{self as module_controller, ModuleAction};
use crate::errors::AppError;
use tauri::AppHandle;

#[tauri::command]
pub async fn get_modules() -> Result<Vec<ModuleItem>, AppError> {
    module_controller::get_all_modules().await
}

#[tauri::command]
pub async fn control_module(
    app: AppHandle,
    request: ControlRequest,
) -> Result<ControlResponse, AppError> {
    let module_id = request
        .module_id
        .as_ref()
        .ok_or_else(|| AppError::Validation("module_id is required".to_string()))?;

    let action: ModuleAction = request.action.parse()?;

    module_controller::control(app, &module_id, action).await
}
