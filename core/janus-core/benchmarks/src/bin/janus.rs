use datafusion::error::Result;
use janus_benchmarks::janus;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(name = "JANUS", about = "JANUS Benchmarks.")]
enum JanusOpt {
    Benchmark(janus::run::RunOpt),
}

#[tokio::main]
async fn main() -> Result<()> {
    env_logger::init();
    match JanusOpt::from_args() {
        JanusOpt::Benchmark(opt) => opt.run().await,
    }
}
