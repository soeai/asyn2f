class NotifyNewModel:
    def __init__(self, chosen_id, model_id, global_model_version, global_model_name, global_model_update_data_size, avg_loss, avg_qod) -> None:
        self.chosen_id = chosen_id
        self.model_id = model_id
        self.global_model_version = global_model_version
        self.global_model_name = global_model_name
        self.global_model_update_data_size = global_model_update_data_size
        self.avg_loss = avg_loss
        self.avg_qod = avg_qod
