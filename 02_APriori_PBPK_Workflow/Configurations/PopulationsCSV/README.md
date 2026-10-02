# Example population CSV files

This folder contains pre-generated Dog, Human, Monkey, Mouse, and Rat population
tables in the column format expected by the OSP/esqlabsR workflow. A file is
loaded only when a scenario explicitly references it; files in this directory
are not discovered or applied automatically.

Keep the parameter-path column names and units unchanged when reusing or
replacing these tables. The current `03_Study_Simulations` analysis creates its
own 50-monkey base population from `Configurations/Populations.xlsx` and does
not read these CSV files.
