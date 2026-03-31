"""Репозиторий для высокопроизводительного чтения агрегированных данных клиента (CQRS Query Layer)."""

from uuid import UUID

from shared.database_core.base_query_repository import BaseQueryRepository
from shared.schemas.customer import FullProfileResponse
from shared.utils.security import decrypt_data


class CustomerQueryRepository(BaseQueryRepository):
	"""Репозиторий для получения полной карточки клиента через сырой SQL."""

	async def get_full_profile(self, user_id: UUID) -> FullProfileResponse | None:
		"""Собирает данные из 5 таблиц (users, personal_data, contacts, passport, identifiers)
		одним эффективным SQL JOIN запросом, обходя оверхед ORM.

		Args:
			user_id: ID клиента.

		Returns:
			FullProfileResponse | None: Агрегированные расшифрованные данные профиля или None.
		"""
		params = {"client_id": user_id}
		
		# Оптимизированный запрос агрегации
		query = """
			SELECT 
				u.id, u.status, u.created_at,
				pd.last_name, pd.first_name, pd.middle_name, pd.birth_date, pd.gender,
				c.email, c.phone,
				p.series as passport_series, p.number as passport_number,
				i.inn, i.snils
			FROM users u
			LEFT JOIN personal_data pd ON pd.client_id = u.id
			LEFT JOIN contacts c ON c.client_id = u.id
			LEFT JOIN passport p ON p.client_id = u.id
			LEFT JOIN identifiers i ON i.client_id = u.id
			WHERE u.id = :client_id
		"""
		
		row = await self._fetch_one(query, params)
		if not row:
			return None

		# Raw SQL не применяет TypeDecorator (EncryptedString), поэтому 
		# расшифровываем чувствительные данные вручную в Query-слое.
		data = dict(row)
		
		# Расшифровка PII полей (Фамилия, Имя, Отчество, Email, Телефон, Паспорт)
		encrypted_fields = [
			"last_name", "first_name", "middle_name", 
			"email", "phone", 
			"passport_series", "passport_number"
		]
		
		for field in encrypted_fields:
			if data.get(field):
				try:
					data[field] = decrypt_data(data[field])
				except Exception:
					# В случае ошибки дешифрования (например, поврежденные данные)
					# оставляем как есть или помечаем [error], чтобы не падать.
					pass

		return FullProfileResponse.model_validate(data)
