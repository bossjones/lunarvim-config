vim.o.lines = 50
vim.o.columns = 160
vim.o.more = false
vim.o.swapfile = false
vim.o.confirm = false

local function check(name, status, message)
  return { name = name, status = status, message = message or "" }
end

local function require_string(name, value)
  if type(value) ~= "string" or value == "" then
    error(name .. " must be a non-empty string")
  end
  return value
end

local function report_path()
  return require_string("SMOKE_OUT", SMOKE_OUT)
end

local function write_report(report)
  local handle, err = io.open(report_path(), "w")
  if handle == nil then
    error("failed to open smoke report: " .. tostring(err))
  end

  handle:write(vim.fn.json_encode(report))
  handle:close()
end

local function runner_dir()
  return vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":h")
end

local function load_manifest()
  local manifest = dofile(runner_dir() .. "/manifest.lua")
  if type(manifest) ~= "table" then
    error("manifest.lua must return a table")
  end
  return manifest
end

local function selected_entries(entries)
  local only = type(SMOKE_ONLY) == "string" and SMOKE_ONLY or ""
  if only == "" then
    return entries
  end

  local selected = {}
  local pattern = vim.fn.glob2regpat(only)
  for _, entry in ipairs(entries) do
    if type(entry) == "table" and vim.fn.match(entry.path, pattern) >= 0 then
      table.insert(selected, entry)
    end
  end
  return selected
end

local function run_fixture(root, entry)
  local path = root .. "/" .. entry.path
  local checks = {}

  vim.cmd("silent! enew!")
  vim.bo.filetype = ""
  vim.v.errmsg = ""

  local opened, err = pcall(vim.cmd.edit, vim.fn.fnameescape(path))
  local current_path = vim.api.nvim_buf_get_name(0)
  local open_status = opened and current_path == path and "pass" or "fail"
  local open_error = ""
  if not opened then
    open_error = tostring(err)
  elseif current_path ~= path then
    open_error = string.format("expected buffer %s, got %s", path, current_path)
  end
  table.insert(checks, check("opens", open_status, open_error))

  local ft_got = vim.bo.filetype
  table.insert(
    checks,
    check("filetype", ft_got == entry.ft and "pass" or "fail", string.format("expected %s, got %s", entry.ft, ft_got))
  )

  return { path = entry.path, ft_got = ft_got, checks = checks }
end

local function run()
  local root = require_string("SMOKE_ROOT", SMOKE_ROOT)
  require_string("SMOKE_MODE", SMOKE_MODE)
  local results = {}

  for _, entry in ipairs(selected_entries(load_manifest())) do
    table.insert(results, run_fixture(root, entry))
  end

  return { results = results }
end

local ok, result = xpcall(run, function(err)
  return debug.traceback(tostring(err), 2)
end)

write_report(ok and result or { runner_error = result, results = {} })
