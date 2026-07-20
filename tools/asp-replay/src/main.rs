use std::fs::OpenOptions;
use std::io::{self, Read};
use std::path::PathBuf;
use std::process::ExitCode;

use asp_replay::{MAX_INPUT_BYTES, self_check, verify};
use clap::{Parser, Subcommand};
#[cfg(unix)]
use std::os::unix::fs::OpenOptionsExt;

#[derive(Debug, Parser)]
#[command(
    name = "asp-replay",
    version,
    about = "Verify and deterministically replay one inert ASP evidence bundle"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Verify one replay bundle and emit a deterministic JSON report. Use - for stdin.
    Verify { bundle: String },
    /// Validate compiled schemas, registries, cases, fixtures, and golden reports.
    SelfCheck {
        #[arg(long, default_value = ".")]
        root: PathBuf,
    },
}

fn read_bounded(source: &str) -> Result<Vec<u8>, String> {
    let bytes = if source == "-" {
        let mut bytes = Vec::new();
        io::stdin()
            .take((MAX_INPUT_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|error| format!("cannot read standard input: {error}"))?;
        bytes
    } else {
        let mut options = OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        options.custom_flags(libc::O_NONBLOCK);
        let file = options
            .open(source)
            .map_err(|error| format!("cannot open {source}: {error}"))?;
        let metadata = file
            .metadata()
            .map_err(|error| format!("cannot inspect {source}: {error}"))?;
        if !metadata.file_type().is_file() {
            return Err(format!("input {source} is not a regular file"));
        }
        let mut bytes = Vec::new();
        file.take((MAX_INPUT_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|error| format!("cannot read {source}: {error}"))?;
        bytes
    };
    if bytes.len() > MAX_INPUT_BYTES {
        return Err(format!("input exceeds {MAX_INPUT_BYTES} bytes"));
    }
    Ok(bytes)
}

fn main() -> ExitCode {
    match Cli::parse().command {
        Command::Verify { bundle } => {
            let bytes = match read_bounded(&bundle) {
                Ok(bytes) => bytes,
                Err(error) => {
                    eprintln!("asp-replay: {error}");
                    return ExitCode::from(2);
                }
            };
            let report = match verify(&bundle, &bytes) {
                Ok(report) => report,
                Err(error) => {
                    eprintln!("asp-replay: {error}");
                    return ExitCode::from(2);
                }
            };
            match serde_json::to_string_pretty(&report) {
                Ok(output) => println!("{output}"),
                Err(error) => {
                    eprintln!("asp-replay: cannot serialize report: {error}");
                    return ExitCode::from(2);
                }
            }
            if report.verdict == "valid" {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
        Command::SelfCheck { root } => match self_check(&root) {
            Ok(()) => {
                println!("ASP replay tool self-check passed");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("asp-replay: {error}");
                ExitCode::from(2)
            }
        },
    }
}
