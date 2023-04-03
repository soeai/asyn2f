class DIContainer:

    @staticmethod
    def add_dependencies(object_type, instance):
        setattr(DIContainer, object_type.__name__, instance)

    @staticmethod
    def get_instance_of(object_type):
        if DIContainer.__dict__[object_type.__name__] is not None:
            return DIContainer.__dict__[object_type.__name__]
        return None


class Controller:
    def __init__(self):
        self.value = 0


di_container = DIContainer()
di_container.add_dependencies(Controller, Controller())
controller: Controller = di_container.get_instance_of(Controller)

print(controller.value)

controller2: Controller = di_container.get_instance_of(Controller)
controller2.value += 3
controller2.value += 10

print(controller.value)

print(DIContainer.get_instance_of(object_type=Controller).value)
