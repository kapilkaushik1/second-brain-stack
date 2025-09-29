"""Main CLI application for the Second Brain Stack."""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from core.utils import get_logger
from core.utils.config import get_settings, Settings
from core.database import DatabaseManager
from core.embeddings import EmbeddingGenerator


console = Console()
logger = get_logger("CLI")


@click.group(invoke_without_command=True)
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context, config: Optional[str], debug: bool):
    """Second Brain Stack CLI - Manage your knowledge base."""
    # Store in context for subcommands first
    ctx.ensure_object(dict)
    
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold blue]Second Brain Stack CLI[/bold blue]\n\n"
            "A comprehensive knowledge management system\n"
            "Use --help to see available commands",
            title="Welcome"
        ))
        return
    
    # Configure settings based on options
    try:
        if config:
            # Load custom config
            settings = Settings.from_yaml(config)
        else:
            settings = get_settings()
        
        if debug:
            settings.debug = True
        
        # Create necessary directories
        settings.create_directories()
        
        # Store settings in context
        ctx.obj['settings'] = settings
        
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        logger.error(f"Configuration failed: {str(e)}")
        ctx.exit(1)


@main.group()
def ingest():
    """Data ingestion commands."""
    pass


@ingest.command()
@click.option("--source", "-s", required=True, 
              type=click.Choice(["filesystem", "web", "git", "api"]),
              help="Data source type")
@click.option("--path", "-p", help="Source path or URL")
@click.option("--recursive", "-r", is_flag=True, help="Recursive processing")
@click.option("--batch-size", "-b", default=10, help="Processing batch size")
@click.option("--file-types", help="Comma-separated file extensions (e.g., .txt,.md,.pdf)")
@click.pass_context
def add(ctx, source: str, path: str, recursive: bool, batch_size: int, file_types: Optional[str]):
    """Add content from various sources."""
    
    if not path:
        path = Prompt.ask(f"Enter {source} path or URL")
    
    console.print(f"[green]Starting {source} ingestion...[/green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=None)
        
        # Run the actual ingestion
        asyncio.run(_run_ingestion(source, path, recursive, batch_size, file_types, progress, task))


async def _run_ingestion(source: str, path: str, recursive: bool, batch_size: int, 
                        file_types: Optional[str], progress, task):
    """Run the ingestion process."""
    try:
        db = DatabaseManager()
        await db.create_tables()
        
        if source == "filesystem":
            await _ingest_filesystem(db, path, recursive, file_types, progress, task)
        elif source == "web":
            await _ingest_web(db, path, progress, task)
        elif source == "git":
            await _ingest_git(db, path, progress, task)
        else:
            console.print(f"[red]Source type {source} not yet implemented[/red]")
            return
        
        # Show completion stats
        stats = await db.get_stats()
        console.print(f"[green]Ingestion complete![/green]")
        console.print(f"Total documents: {stats['documents']}")
        
    except Exception as e:
        console.print(f"[red]Ingestion failed: {str(e)}[/red]")
        logger.error(f"Ingestion failed: {str(e)}")


async def _ingest_filesystem(db: DatabaseManager, path: str, recursive: bool, 
                           file_types: Optional[str], progress, task):
    """Ingest from filesystem."""
    from connectors.filesystem.scanner import FilesystemScanner
    
    scanner = FilesystemScanner(
        supported_types=file_types.split(",") if file_types else None
    )
    
    progress.update(task, description="Scanning files...")
    files = await scanner.scan_directory(Path(path), recursive=recursive)
    
    progress.update(task, description=f"Processing {len(files)} files...", total=len(files))
    
    processed = 0
    for file_path in files:
        try:
            document = await scanner.process_file(file_path)
            if document:
                await db.create_document(document)
                processed += 1
            progress.advance(task)
        except Exception as e:
            logger.error(f"Failed to process file {str(file_path)}: {str(e)}")
    
    console.print(f"[green]Processed {processed} files successfully[/green]")


async def _ingest_web(db: DatabaseManager, url: str, progress, task):
    """Ingest from web."""
    console.print(f"[yellow]Web ingestion not yet implemented[/yellow]")


async def _ingest_git(db: DatabaseManager, path: str, progress, task):
    """Ingest from git repository."""
    console.print(f"[yellow]Git ingestion not yet implemented[/yellow]")


@main.group()
def search():
    """Search commands."""
    pass


@search.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Number of results to return")
@click.option("--type", "-t", default="hybrid", 
              type=click.Choice(["fulltext", "semantic", "hybrid"]),
              help="Search type")
@click.option("--threshold", default=0.7, help="Similarity threshold for semantic search")
def query(query: str, limit: int, type: str, threshold: float):
    """Search the knowledge base."""
    asyncio.run(_run_search(query, limit, type, threshold))


async def _run_search(query: str, limit: int, search_type: str, threshold: float):
    """Run search query."""
    try:
        db = DatabaseManager()
        
        console.print(f"[blue]Searching for: '{query}'[/blue]")
        console.print(f"Search type: {search_type}, Limit: {limit}")
        
        if search_type in ["fulltext", "hybrid"]:
            # Full-text search
            fts_results = await db.fulltext_search(query, limit)
            
            if fts_results:
                console.print("\n[green]Full-text search results:[/green]")
                _display_search_results(fts_results)
        
        if search_type in ["semantic", "hybrid"]:
            # Semantic search
            embedding_gen = EmbeddingGenerator()
            query_embedding = embedding_gen.encode_single(query)
            
            vector_results = await db.vector_search(query_embedding, limit, threshold)
            
            if vector_results:
                console.print("\n[green]Semantic search results:[/green]")
                _display_search_results(vector_results)
        
        if not fts_results and not vector_results:
            console.print("[yellow]No results found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Search failed: {str(e)}[/red]")
        logger.error(f"Search failed: {str(e)}")


def _display_search_results(results):
    """Display search results in a nice format."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Score", style="cyan", width=8)
    table.add_column("Title", style="green")
    table.add_column("Source", style="blue")
    table.add_column("Preview", style="dim")
    
    for doc, score in results[:10]:  # Show top 10
        preview = doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
        table.add_row(
            f"{score:.3f}",
            doc.title[:50],
            doc.source_type,
            preview
        )
    
    console.print(table)


@main.command()
def chat():
    """Start an interactive chat session."""
    asyncio.run(_run_chat())


async def _run_chat():
    """Run interactive chat."""
    console.print(Panel.fit(
        "[bold blue]Second Brain Chat[/bold blue]\n\n"
        "Ask questions about your knowledge base.\n"
        "Type 'exit' or 'quit' to end the session.",
        title="Chat Mode"
    ))
    
    db = DatabaseManager()
    session_id = f"cli-{asyncio.get_event_loop().time()}"
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You")
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            # For now, just echo back - real chat implementation would be more complex
            console.print(f"[green]Bot:[/green] I understand you're asking about: '{user_input}'")
            console.print("[dim]Note: Full chat functionality requires the chat service to be running.[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session ended.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@main.group()
def db():
    """Database management commands."""
    pass


@db.command()
def init():
    """Initialize the database."""
    asyncio.run(_init_database())


async def _init_database():
    """Initialize database tables."""
    try:
        console.print("[blue]Initializing database...[/blue]")
        db = DatabaseManager()
        await db.create_tables()
        console.print("[green]Database initialized successfully![/green]")
    except Exception as e:
        console.print(f"[red]Database initialization failed: {str(e)}[/red]")


@db.command()
def stats():
    """Show database statistics."""
    asyncio.run(_show_stats())


async def _show_stats():
    """Show database statistics."""
    try:
        db = DatabaseManager()
        stats = await db.get_stats()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print("\n")
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get stats: {str(e)}[/red]")


@main.group()
def config():
    """Configuration management."""
    pass


@config.command()
def show():
    """Show current configuration."""
    settings = get_settings()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Show key settings
    config_items = [
        ("Database Path", settings.database.path),
        ("FTS Enabled", settings.database.fts_enabled),
        ("Embedding Model", settings.embeddings.model_name),
        ("Vector Dimensions", settings.embeddings.vector_dimensions),
        ("Debug Mode", settings.debug),
    ]
    
    for key, value in config_items:
        table.add_row(key, str(value))
    
    console.print("\n")
    console.print(table)


@config.command() 
def create():
    """Create a sample configuration file."""
    config_content = """database:
  path: "storage/brain.db"
  wal_mode: true
  fts_enabled: true

services:
  ingestion:
    port: 8001
    workers: 4
  
  search:
    port: 8002
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  
  knowledge:
    port: 8003
    entity_model: "en_core_web_sm"
    
  chat:
    port: 8004

embeddings:
  model_path: "storage/models/"
  cache_size: 1000
  batch_size: 32

connectors:
  supported_file_types: [".txt", ".md", ".pdf", ".py"]
  max_file_size: "50MB"
"""
    
    config_file = Path("brain.yml")
    if config_file.exists():
        if not Prompt.ask("Configuration file exists. Overwrite?", choices=["y", "n"], default="n") == "y":
            return
    
    config_file.write_text(config_content)
    console.print(f"[green]Configuration file created: {config_file}[/green]")


if __name__ == "__main__":
    main()