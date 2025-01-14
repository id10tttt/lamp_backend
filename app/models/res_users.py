# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Annotated


class ResUsers(BaseModel):

    name: Annotated[str, Field(min_length=1)]
    login: Annotated[str, Field(min_length=1)]