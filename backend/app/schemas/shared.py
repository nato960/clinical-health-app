from typing import Optional

from pydantic import BaseModel

class AddressSchema(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    model_config = {'from_attributes': True}