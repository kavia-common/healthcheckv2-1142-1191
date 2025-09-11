"""
Alias CLI module for backward-compatible imports.

Re-exports 'main' from healthcheckv2.healthcheck_cli so that:
    from healthcheck.healthcheck_cli import main
continues to work.
"""

# PUBLIC_INTERFACE
def main(argv=None):
    """CLI main entrypoint alias forwarding to healthcheckv2.healthcheck_cli.main.

    Args:
        argv: Optional list of CLI args.

    Returns:
        int: Exit code from the underlying CLI.
    """
    from healthcheckv2.healthcheck_cli import main as _v2_main
    return _v2_main(argv)
