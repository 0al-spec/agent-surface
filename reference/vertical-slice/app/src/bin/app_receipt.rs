use asp_reference_vertical_app::{RP, run_subject};

fn main() {
    if let Err(error) = run_subject(&[RP]) {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
