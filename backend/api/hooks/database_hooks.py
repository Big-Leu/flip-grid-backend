# from typing import Any

# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.ext.asyncio import AsyncSession

# from backend.commons.responses import ServiceResponse, ServiceResponseStatus
# from backend.services.business_unit.crud import BusinessUnitsService


# async def create_business_units(session: AsyncSession) -> list[ServiceResponse]:
#     business_units_data = {
#         "BU001": "Consumer Banking",
#         "BU002": "Commercial Banking",
#         "BU003": "Consumer Payment",
#         "BU004": "Wholesale Payment",
#         "BU005": "Mortgage",
#         "BU006": "Data",
#         "BU007": "Customer Services",
#         "BU008": "Finance",
#         "BU009": "Wealth",
#         "BU010": "Investment Management",
#         "BU011": "M&A",
#     }
#     response: list[Any] = []
#     for key, value in business_units_data.items():
#         continue
#         try:
#             bu = BusinessUnitsService(session)

#             resp = await bu.check_business_unit(key)
#             if resp.status == ServiceResponseStatus.EXISTS:
#                 # Business unit already exists
#                 continue
#             else:
#                 response.append(
#                     await bu.create(business_unit_id=key, business_unit_name=value)
#                 )
#                 print(response)
#         except IntegrityError as ex:
#             if str(ex).find("duplicate key value violates unique constraint") != -1:
#                 # We are getting duplicate data error
#                 pass

#     return response


# async def run_db_initialize_hooks(session: AsyncSession) -> list[ServiceResponse]:
#     return await create_business_units(session)
