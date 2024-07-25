import json

def serializable(cls):
    """Класс декоратора, который добавляет методы сериализации и десериализации"""
    cls._serializable_fields = []
    return cls

def serialize(func):
    """Декоратор для маркировки свойств, которые должны быть сериализованы"""
    func._is_serializable = True
    return func

@serializable
class Settings:
    def __init__(self):
        self._username = "default_user"
        self._password = "default_pass"
        self._temp_data = "some_temp_data"

    @property
    @serialize
    def username(self):
        return self._username
    @username.setter
    def username(self, value):
        self._username = value

    @property
    @serialize
    def password(self):
        return self._password
    @password.setter
    def password(self, value):
        self._password = value

    @property
    def temp_data(self):
        return self._temp_data
    @temp_data.setter
    def temp_data(self, value):
        self._temp_data = value

    def to_dict(self):
        """Метод для сериализации только маркированных свойств"""
        data = {}
        for name, method in self.__class__.__dict__.items():
            if isinstance(method, property) and getattr(method.fget, '_is_serializable', False):
                data[name] = getattr(self, name)
        return data

    def to_json(self):
        """Метод для сериализации в JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        """Метод для десериализации из словаря"""
        instance = cls()
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        return instance

    @classmethod
    def from_json(cls, json_data):
        """Метод для десериализации из JSON"""
        data = json.loads(json_data)
        return cls.from_dict(data)

# Пример использования
settings = Settings()
settings.username = "new_user"
settings.password = "new_pass"
settings.temp_data = "new_temp_data"
print(settings.to_json())  # {"username": "new_user", "password": "new_pass"}

serialized_data = settings.to_json()
new_settings = Settings.from_json(serialized_data)
print(new_settings.username)  # new_user
print(new_settings.password)  # new_pass
print(new_settings.temp_data)  # some_temp_data (это свойство не было сериализовано и использует значение по умолчанию)
