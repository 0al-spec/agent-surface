use std::fs;
use std::io::{self, Read};
use std::path::PathBuf;
use std::process::ExitCode;

use asp_api_importer::{generate_manifest, render_manifest, self_check};
use clap::{Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(
    name = "asp-api-import",
    version,
    about = "Generate an ASP manifest candidate from explicit OpenAPI or AsyncAPI annotations"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Generate one deterministic ASP manifest candidate. Use - to read standard input.
    Generate { source: String },
    /// Validate compiled schemas, the case registry, fixtures, and golden output.
    SelfCheck {
        #[arg(long, default_value = ".")]
        root: PathBuf,
    },
}

fn read_source(source: &str) -> Result<String, String> {
    if source == "-" {
        let mut document = String::new();
        io::stdin()
            .read_to_string(&mut document)
            .map_err(|error| format!("cannot read standard input: {error}"))?;
        Ok(document)
    } else {
        fs::read_to_string(source).map_err(|error| format!("cannot read {source}: {error}"))
    }
}

fn main() -> ExitCode {
    match Cli::parse().command {
        Command::Generate { source } => {
            let document = match read_source(&source) {
                Ok(document) => document,
                Err(error) => {
                    eprintln!("asp-api-import: {error}");
                    return ExitCode::from(2);
                }
            };
            let manifest = match generate_manifest(&source, &document) {
                Ok(manifest) => manifest,
                Err(error) => {
                    eprintln!("asp-api-import: {error}");
                    return ExitCode::from(2);
                }
            };
            match render_manifest(&manifest) {
                Ok(output) => print!("{output}"),
                Err(error) => {
                    eprintln!("asp-api-import: {error}");
                    return ExitCode::from(2);
                }
            }
            ExitCode::SUCCESS
        }
        Command::SelfCheck { root } => match self_check(&root) {
            Ok(()) => {
                println!("ASP API importer self-check passed");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("asp-api-import: {error}");
                ExitCode::from(2)
            }
        },
    }
}
