import click

@click.group()
def cli():
    """luks-keeper: Secure LUKS passphrase manager."""
    pass

if __name__ == "__main__":
    cli()

