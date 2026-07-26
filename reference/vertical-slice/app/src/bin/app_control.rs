use asp_reference_vertical_app::{GI, SP, run_subject};

fn main() {
    if let Err(error) = run_subject(&[SP, GI]) {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
