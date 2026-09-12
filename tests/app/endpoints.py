from typing import List

from litestar import MediaType, get, post
from piccolo.testing import ModelBuilder

from litestar_piccolo import PiccoloDTO
from tests.app.tables import Band, Concert, Manager, RecordingStudio, Venue

studio = ModelBuilder.build_sync(RecordingStudio, persist=False)
venues = [ModelBuilder.build_sync(Venue, persist=False) for _ in range(3)]
band = Band(id=1, name="Pythonistas", popularity=1000)
band.manager = Manager(id=1, name="Guido")
band_without_related_manager = Band(id=2, name="Rustaceans", manager=1, popularity=500)


@post("/concert", dto=PiccoloDTO[Concert], return_dto=PiccoloDTO[Concert], media_type=MediaType.JSON)
async def create_concert(data: Concert) -> Concert:
    await data.save()
    await data.refresh()
    return data


@get("/studio", return_dto=PiccoloDTO[RecordingStudio], sync_to_thread=False)
def retrieve_studio() -> RecordingStudio:
    return studio


@get("/venues", return_dto=PiccoloDTO[Venue], sync_to_thread=False)
def retrieve_venues() -> List[Venue]:
    return venues


@get("/plugin/studio")
async def retrieve_studio_plugin() -> RecordingStudio:
    return studio


@get("/plugin/venues")
async def retrieve_venues_plugin() -> List[Venue]:
    return venues


@get("/band", return_dto=PiccoloDTO[Band], sync_to_thread=False)
def retrieve_band() -> Band:
    return band


@get("/band-without-related-manager", return_dto=PiccoloDTO[Band], sync_to_thread=False)
def retrieve_band_without_related_manager() -> Band:
    return band_without_related_manager
