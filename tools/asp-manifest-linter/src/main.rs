use std::fs;
use std::io::{self, Read};
use std::path::PathBuf;
use std::process::ExitCode;

use asp_manifest_linter::{lint_manifest, render_text, self_check};
use clap::{Parser, Subcommand, ValueEnum};

#[derive(Debug, Parser)]
#[command(
    name = "asp-lint",
    version,
    about = "Lint Agent Surface Protocol manifests"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Check one ASP manifest. Use - to read standard input.
    Check {
        manifest: String,
        #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
        format: OutputFormat,
    },
    /// Validate the compiled rules, schemas, and implementation bindings.
    SelfCheck {
        #[arg(long, default_value = ".")]
        root: PathBuf,
    },
}

#[derive(Clone, Copy, Debug, ValueEnum)]
enum OutputFormat {
    Text,
    Json,
}

fn read_manifest(source: &str) -> Result<String, String> {
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
        Command::Check { manifest, format } => {
            let document = match read_manifest(&manifest) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("asp-lint: {error}");
                    return ExitCode::from(2);
                }
            };
            let report = match lint_manifest(&manifest, &document) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("asp-lint: {error}");
                    return ExitCode::from(2);
                }
            };
            match format {
                OutputFormat::Text => print!("{}", render_text(&report)),
                OutputFormat::Json => match serde_json::to_string_pretty(&report) {
                    Ok(value) => println!("{value}"),
                    Err(error) => {
                        eprintln!("asp-lint: cannot serialize report: {error}");
                        return ExitCode::from(2);
                    }
                },
            }
            if report.diagnostics.is_empty() {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
        Command::SelfCheck { root } => match self_check(&root) {
            Ok(()) => {
                println!("ASP manifest linter self-check passed");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("asp-lint: {error}");
                ExitCode::from(2)
            }
        },
    }
}
