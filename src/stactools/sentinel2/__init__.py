import stactools.core

stactools.core.use_fsspec()


def register_plugin(registry):
    # Register subcommands

    from stactools.sentinel2 import commands

    registry.register_subcommand(commands.create_sentinel2_command)


__version__ = "0.4.2"
