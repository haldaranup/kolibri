import logging.config
import os
import sys

from configobj import ConfigObj
from configobj import flatten_errors
from configobj import get_extra_values
from validate import Validator


option_spec = {
    "Database": {
        "DATABASE_ENGINE": {
            "type": "option",
            "options": ("sqlite", "postgres"),
            "default": "sqlite",
            "envvars": ("KOLIBRI_DATABASE_ENGINE",),
        },
        "DATABASE_NAME": {
            "type": "string",
            "envvars": ("KOLIBRI_DATABASE_NAME",),
        },
        "DATABASE_PASSWORD": {
            "type": "string",
            "envvars": ("KOLIBRI_DATABASE_PASSWORD",),
        },
        "DATABASE_USER": {
            "type": "string",
            "envvars": ("KOLIBRI_DATABASE_USER",),
        },
        "DATABASE_HOST": {
            "type": "string",
            "envvars": ("KOLIBRI_DATABASE_HOST",),
        },
    },
    "Paths": {
        "CONTENT_DIR": {
            "type": "string",
            "default": "content",
            "envvars": ("KOLIBRI_CONTENT_DIR",),
        },
    },
    "Deployment": {
        "HTTP_LISTEN_PORT": {
            "type": "integer",
            "default": 8080,
            "envvars": ("KOLIBRI_HTTP_LISTEN_PORT", "KOLIBRI_LISTEN_PORT"),
        },
        "RUN_MODE": {
            "type": "string",
            "envvars": ("KOLIBRI_RUN_MODE",),
        }
    },
}


def get_logging_config(KOLIBRI_HOME):
    """
    We define a minimal default logger config here, since we can't yet load up Django settings.
    """
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple_date': {
                'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
            },
            'color': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(log_color)s%(levelname)-8s %(message)s',
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'color'
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': os.path.join(KOLIBRI_HOME, 'kolibri.log'),
                'formatter': 'simple_date',
            },
        },
        'loggers': {
            'kolibri': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
            },
        }
    }


def get_configspec():
    """
    Read the option_spec dict defined above, and turn it into a "configspec" object (per the configobj library)
    so that we can use it to parse the options.ini file.
    """

    lines = []

    for section, opts in option_spec.items():
        lines.append("[{section}]".format(section=section))
        for name, attrs in opts.items():
            default = attrs.get("default", "")
            the_type = attrs["type"]
            args = ["%r" % op for op in attrs.get("options", [])] + ["default='{default}'".format(default=default)]
            line = "{name} = {type}({args})".format(name=name, type=the_type, args=", ".join(args))
            lines.append(line)

    return ConfigObj(lines, _inspec=True)


def read_options_file(KOLIBRI_HOME, ini_filename="options.ini"):

    # load up and configure the logger
    logging.config.dictConfig(get_logging_config(KOLIBRI_HOME))
    logger = logging.getLogger(__name__)

    ini_path = os.path.join(KOLIBRI_HOME, ini_filename)

    conf = ConfigObj(ini_path, configspec=get_configspec())

    # validate once up front to ensure section structure is in place
    conf.validate(Validator())

    # keep track of which options were overridden using environment variables, to support error reporting
    using_env_vars = {}

    # override any values from their environment variables (if set)
    for section, opts in option_spec.items():
        for optname, attrs in opts.items():
            for envvar in attrs.get("envvars", []):
                if os.environ.get(envvar):
                    logger.info("Option {optname} in section [{section}] being overridden by environment variable {envvar}"
                                .format(optname=optname, section=section, envvar=envvar))
                    conf[section][optname] = os.environ[envvar]
                    using_env_vars[optname] = envvar
                    break

    validation = conf.validate(Validator(), preserve_errors=True)

    # loop over and display any errors with config values, and then bail
    if validation is not True:
        for section_list, optname, error in flatten_errors(conf, validation):
            section = section_list[0]
            if optname in using_env_vars:
                logger.error("Error processing environment variable option {envvar}: {error}"
                             .format(envvar=using_env_vars[optname], error=error))
            else:
                logger.error("Error processing {file} under section [{section}] for option {option}: {error}"
                             .format(file=ini_path, section=section, option=optname, error=error))
        logger.critical("Aborting: Could not process options config (see errors above for more details)")
        sys.exit(1)

    # loop over any extraneous options and warn the user that we're ignoring them
    for sections, name in get_extra_values(conf):

        # this code gets the extra values themselves
        the_section = conf
        for section in sections:
            the_section = the_section[section]

        # the_value may be a section or a value
        the_value = the_section.pop(name)

        # determine whether the extra item is a section (dict) or value
        kind = 'section' if isinstance(the_value, dict) else 'option'

        logger.warn("Ignoring unknown {kind} in options file {file} under {section}: {name}."
                    .format(kind=kind, file=ini_path, section=sections[0] if sections else "top level", name=name))

    # run validation once again to fill in any default values for options we deleted due to issues
    conf.validate(Validator())

    return conf
