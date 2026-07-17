from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import CastingControls, CastingPresetCollection, CastingPresetRecord


class CastingPresetNotFoundError(LookupError):
    pass


class CastingPresetConfigurationError(RuntimeError):
    pass


class CastingPresetCatalog:
    """Validated, immutable casting art direction loaded from the committed seed."""

    def __init__(self, collection: CastingPresetCollection) -> None:
        self.collection = collection
        self._presets = {preset.id: preset for preset in collection.presets}
        if len(self._presets) != len(collection.presets):
            raise CastingPresetConfigurationError("Casting preset ids must be unique.")
        advertised_controls = set(collection.variation_controls) - {"default"}
        supported_controls = set(CastingControls.model_fields)
        if advertised_controls != supported_controls:
            raise CastingPresetConfigurationError(
                "Casting preset controls must match the API control contract."
            )
        try:
            for field_name in supported_controls:
                values = collection.variation_controls[field_name]
                if not isinstance(values, list):
                    raise CastingPresetConfigurationError(
                        "Each casting control must advertise a list of values."
                    )
                for value in values:
                    CastingControls.model_validate({field_name: value})
        except ValidationError as error:
            raise CastingPresetConfigurationError(
                "Casting preset controls contain an unsupported value."
            ) from error
        policy = collection.subject_policy
        if not (
            policy.adults_only
            and policy.minimum_apparent_age >= 25
            and policy.fictional_people_only
            and not policy.real_person_references_allowed
            and policy.preserve_garment_design
            and policy.presentation_is_separate_asset
        ):
            raise CastingPresetConfigurationError(
                "Casting presets must enforce fictional adults and immutable garments."
            )

    @classmethod
    def load(cls, path: Path) -> CastingPresetCatalog:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            collection = CastingPresetCollection.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise CastingPresetConfigurationError(
                "The casting preset collection could not be loaded."
            ) from error
        return cls(collection)

    def get(self, preset_id: str) -> CastingPresetRecord:
        try:
            return self._presets[preset_id]
        except KeyError as error:
            raise CastingPresetNotFoundError(preset_id) from error
