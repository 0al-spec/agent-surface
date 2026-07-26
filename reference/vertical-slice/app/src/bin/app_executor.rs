use asp_reference_vertical_app::{AE, run_subject};

fn main() {
    if let Err(error) = run_subject(&[AE]) {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
