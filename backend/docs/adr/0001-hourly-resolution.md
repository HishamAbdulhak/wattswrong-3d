# 0001 Hourly resolution

Status: adopted (team master prompt overrides the SUGGESTED 15 minutes in the handoff config).

Pipeline and exports use 60-minute periods. Reason: fewer rows, faster LightGBM, simpler charts, and still plenty for comparing detection delay against the 15-day bill assumption. `config/config.json` `suggested.period_minutes` = 60.
