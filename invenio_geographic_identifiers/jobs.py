# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Jobs for the geographic identifiers vocabularies."""

from copy import deepcopy

from invenio_i18n import lazy_gettext as _
from invenio_jobs.jobs import JobType, PredefinedArgsSchema
from marshmallow import fields

from .contrib.geonames.datastreams import DATASTREAM_CONFIG as geonames_ds_config
from .tasks import import_geoidentifiers_sharded


class ImportGeoNamesArgsSchema(PredefinedArgsSchema):
    """Arguments of a GeoNames import."""

    job_arg_schema = fields.String(
        metadata={"type": "hidden"},
        dump_default="ImportGeoNamesArgsSchema",
        load_default="ImportGeoNamesArgsSchema",
    )

    origin = fields.String(
        load_default=None,
        allow_none=True,
        metadata={
            "description": _(
                "Path or URL of the GeoNames dump. Leave empty to fetch "
                "allCountries.zip from download.geonames.org. It is around "
                "400 MiB, takes a while, and is kept and reused afterwards."
            )
        },
    )

    shards = fields.Integer(
        load_default=1,
        metadata={
            "description": _(
                "How many workers to split the import across. Each reads the "
                "whole dump but writes only its own share."
            )
        },
    )

    feature_classes = fields.String(
        load_default=None,
        allow_none=True,
        metadata={
            "description": _(
                "Comma-separated feature classes to keep, e.g. 'P,A' for "
                "populated places and administrative divisions. All by default."
            )
        },
    )

    refresh = fields.Boolean(
        load_default=False,
        metadata={
            "description": _(
                "Fetch the dump again even if a copy was already downloaded. "
                "GeoNames rebuilds it daily; a copy is otherwise reused."
            )
        },
    )


class ImportGeoNamesJob(JobType):
    """Import the GeoNames vocabulary."""

    id = "import_geonames"
    """The job id."""

    title = _("Import GeoNames")
    """The job title."""

    description = _("Load geographic identifiers from a GeoNames dump")
    """The job description."""

    task = import_geoidentifiers_sharded
    """The task to run."""

    arguments_schema = ImportGeoNamesArgsSchema
    """The arguments schema."""

    @classmethod
    def build_task_arguments(
        cls,
        job_obj,
        since=None,
        origin=None,
        shards=1,
        feature_classes=None,
        refresh=False,
        **kwargs,
    ):
        """Build the datastream configuration for a run.

        Args:
            job_obj: The job object.

            since: The since date.

            origin: The origin.

            shards: The number of shards to split the source into.

            feature_classes: The feature classes to keep.

            refresh: Fetch the source again even if a copy is already here.

            kwargs: The keyword arguments.

        Notes:
            `since` is ignored: a GeoNames dump is a full snapshot with no way to
            ask it for what changed, so every run reads all of it. Entries that
            already exist are rewritten, which is what makes a repeat run an update.
        """
        # Copy the configuration
        config = deepcopy(geonames_ds_config)
        reader_args = config["readers"][0].setdefault("args", {})

        # Set origin, when there is one
        if origin:
            reader_args["origin"] = origin

        # Set feature classes
        if feature_classes:
            reader_args["feature_classes"] = feature_classes

        # Configure the write many flag
        config["write_many"] = True

        # Set update flag
        for writer in config["writers"]:
            writer.setdefault("args", {})["update"] = True

        # Return!
        return {
            "config": config,
            "shards": shards,
            "refresh": bool(refresh),
        }
