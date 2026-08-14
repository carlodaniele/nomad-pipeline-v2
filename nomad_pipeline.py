import os

adapter = os.getenv("NOMAD_PIPELINE_ADAPTER", "wordpress")

if adapter == "wordpress":
    from adapters.wordpress.adapter import run
elif adapter == "astro":
    raise NotImplementedError("Astro adapter not yet implemented.")
else:
    raise ValueError(f"Unknown adapter: {adapter}")

if __name__ == "__main__":
    result = run()
    print(result)