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

local function has_active_highlighter(bufnr)
  local ok, highlighter = pcall(require, "vim.treesitter.highlighter")
  return ok and highlighter.active[bufnr] ~= nil
end

local with_message_evidence
local classify_runtime_messages

local function highlight_check(entry, bufnr)
  if entry.parser then
    local has_parser = require("nvim-treesitter.parsers").has_parser(entry.parser)
    local start_ok, start_err = true, nil
    if has_parser then
      start_ok, start_err = pcall(vim.treesitter.start, bufnr, entry.parser)
    end
    local active = vim.wait(1000, function()
      return has_active_highlighter(bufnr)
    end, 25)
    local status = has_parser and start_ok and active and "pass" or "fail"
    local message = string.format("parser=%s highlighter=%s", tostring(has_parser), tostring(active))
    if not start_ok then
      local start_issue = classify_runtime_messages(tostring(start_err))
      if start_issue ~= nil then
        message = start_issue.label .. ": " .. start_issue.summary
        message = with_message_evidence(message, start_issue.evidence)
      else
        message = message .. " treesitter start error: " .. tostring(start_err)
      end
    end
    return check("highlight", status, message)
  end

  local active = vim.wait(500, function()
    return vim.b[bufnr].current_syntax ~= nil
  end, 25)
  return check("highlight", active and "pass" or "fail", "builtin syntax=" .. tostring(vim.b[bufnr].current_syntax))
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

local function version_parts(version)
  if type(version) == "table" then
    return tonumber(version.major), tonumber(version.minor), tonumber(version.patch) or 0
  end

  local major, minor, patch = tostring(version):match("^(%d+)%.(%d+)%.?(%d*)")
  if major == nil or minor == nil then
    return nil, nil, nil
  end
  return tonumber(major), tonumber(minor), tonumber(patch) or 0
end

local function version_string(major, minor, patch)
  return string.format("%d.%d.%d", major, minor, patch)
end

local function compare_versions(left, right)
  for index = 1, 3 do
    if left[index] < right[index] then
      return -1
    end
    if left[index] > right[index] then
      return 1
    end
  end
  return 0
end

local function current_nvim_version()
  local major, minor, patch = version_parts(vim.version())
  if major == nil then
    error("unable to parse Neovim version")
  end
  return { major, minor, patch }
end

local function version_check(entry, current_version)
  local current = version_string(current_version[1], current_version[2], current_version[3])
  if entry.min_nvim ~= nil then
    local major, minor, patch = version_parts(entry.min_nvim)
    if major == nil then
      error("invalid min_nvim version: " .. tostring(entry.min_nvim))
    end
    if compare_versions(current_version, { major, minor, patch }) < 0 then
      return check("version", "skip", "nvim version " .. current .. " is below minimum " .. tostring(entry.min_nvim))
    end
  end
  if entry.max_nvim ~= nil then
    local major, minor, patch = version_parts(entry.max_nvim)
    if major == nil then
      error("invalid max_nvim version: " .. tostring(entry.max_nvim))
    end
    if compare_versions(current_version, { major, minor, patch }) > 0 then
      return check("version", "skip", "nvim version " .. current .. " is above maximum " .. tostring(entry.max_nvim))
    end
  end
  return nil
end

local function message_snapshot()
  return vim.fn.execute("messages")
end

local function new_messages(snapshot)
  local current = message_snapshot()
  if snapshot == "" then
    return vim.trim(current)
  end
  if vim.startswith(current, snapshot) then
    return vim.trim(current:sub(#snapshot + 1))
  end
  if current == snapshot then
    return ""
  end
  return vim.trim(current)
end

with_message_evidence = function(message, messages)
  if messages == "" then
    return message
  end
  return message .. "\nmessages:\n" .. messages
end

local function with_messages(message, snapshot)
  return with_message_evidence(message, new_messages(snapshot))
end

local runtime_message_patterns = {
  { pattern = "E%d+:", label = "runtime error", category = "generic" },
  { pattern = "stack traceback", label = "runtime traceback", category = "traceback" },
  { pattern = "[Rr][Pp][Cc]", label = "rpc failure", category = "rpc" },
  { pattern = "[Ss]erver exited", label = "server exited", category = "rpc" },
  { pattern = "Client %d+ quit", label = "client quit", category = "rpc" },
  { pattern = "bad argument", label = "runtime error", category = "generic" },
  { pattern = "invalid node type", label = "runtime error", category = "generic" },
  { pattern = "Failed to", label = "runtime error", category = "generic" },
  { pattern = "[Ee]rror", label = "runtime error", category = "generic" },
}

classify_runtime_messages = function(messages)
  if messages == "" then
    return nil
  end

  for _, candidate in ipairs(runtime_message_patterns) do
    for line in vim.gsplit(messages, "\n", true) do
      local trimmed = vim.trim(line)
      if trimmed ~= "" and trimmed:match(candidate.pattern) then
        return {
          label = candidate.label,
          category = candidate.category,
          summary = trimmed,
          evidence = messages,
        }
      end
    end
  end

  return nil
end

local function clients_for(bufnr)
  if vim.lsp.get_clients then
    return vim.lsp.get_clients { bufnr = bufnr }
  end
  return vim.lsp.get_active_clients { bufnr = bufnr }
end

local lsp_bins = {
  ansiblels = "ansible-language-server",
  bashls = "bash-language-server",
  basedpyright = "basedpyright-langserver",
  dockerls = "docker-langserver",
  jsonls = "vscode-json-language-server",
  ruff = "ruff",
  taplo = "taplo",
  vale_ls = "vale-ls",
  yamlls = "yaml-language-server",
}

local formatter_bins = {
  jsonls = lsp_bins.jsonls,
  ruff = lsp_bins.ruff,
  shfmt = "shfmt",
  stylua = "stylua",
}

local function attached_client_names(bufnr)
  local attached = {}
  for _, client in ipairs(clients_for(bufnr)) do
    attached[client.name] = true
  end
  return attached
end

local function joined_names(names)
  return table.concat(names, ", ")
end

local function lsp_checks(entry, bufnr, mode)
  if type(entry.lsp) ~= "table" or vim.tbl_isempty(entry.lsp) then
    return nil, nil
  end

  local missing_bins = {}
  for _, name in ipairs(entry.lsp) do
    local bin = lsp_bins[name]
    if bin ~= nil and vim.fn.executable(bin) == 0 then
      table.insert(missing_bins, bin)
    end
  end

  if not vim.tbl_isempty(missing_bins) then
    local status = mode == "smoke" and "skip" or "fail"
    local message = joined_names(missing_bins) .. " not installed"
    return check("lsp", status, message), check("lsp_healthy", status, message)
  end

  local lsp_snapshot = message_snapshot()
  vim.wait(5000, function()
    local attached = attached_client_names(bufnr)
    for _, name in ipairs(entry.lsp) do
      if not attached[name] then
        return false
      end
    end
    return true
  end, 50)

  local attached = attached_client_names(bufnr)
  local missing_clients = {}
  local attached_names = {}
  for _, name in ipairs(entry.lsp) do
    if attached[name] then
      table.insert(attached_names, name)
    else
      table.insert(missing_clients, name)
    end
  end

  local lsp_status = vim.tbl_isempty(missing_clients) and "pass" or "fail"
  local lsp_message = vim.tbl_isempty(missing_clients)
      and ("attached=" .. joined_names(attached_names))
    or ("missing=" .. joined_names(missing_clients))

  local stopped_clients = {}
  for _, client in ipairs(clients_for(bufnr)) do
    if attached[client.name] and type(client.is_stopped) == "function" and client:is_stopped() then
      table.insert(stopped_clients, client.name)
    end
  end

  local lsp_messages = new_messages(lsp_snapshot)
  local lsp_issue = classify_runtime_messages(lsp_messages)

  local lsp_runtime_failure = lsp_issue ~= nil and lsp_issue.category == "rpc"
  local healthy_status = (#stopped_clients == 0 and not lsp_runtime_failure) and "pass" or "fail"
  local healthy_message = "clients healthy"
  if #stopped_clients > 0 then
    healthy_message = "stopped=" .. joined_names(stopped_clients)
  end
  if lsp_runtime_failure then
    healthy_message = lsp_issue.label .. ": " .. lsp_issue.summary
    healthy_message = with_message_evidence(healthy_message, lsp_issue.evidence)
  elseif #attached_names > 0 then
    healthy_message = healthy_message .. " (" .. joined_names(attached_names) .. ")"
  end

  return check("lsp", lsp_status, lsp_message), check("lsp_healthy", healthy_status, healthy_message)
end

local function edit_check(bufnr, expected_lines)
  local edit_snapshot = message_snapshot()
  local edited = false
  local ok, err = pcall(function()
    vim.api.nvim_win_set_cursor(0, { 1, 0 })
    vim.cmd.startinsert()
    vim.cmd "normal! ggOsmoke"
    edited = true
    vim.cmd "normal! u"
    vim.cmd.stopinsert()
  end)
  local restored = vim.deep_equal(vim.api.nvim_buf_get_lines(bufnr, 0, -1, false), expected_lines)
  local messages = new_messages(edit_snapshot)
  local message_issue = classify_runtime_messages(messages)
  local status = ok and edited and restored and message_issue == nil and "pass" or "fail"
  local message = restored and "insert/undo restored buffer" or "insert/undo did not restore original buffer"
  if not ok then
    message = message .. " error=" .. tostring(err)
  end
  if message_issue ~= nil then
    message = message_issue.label .. ": " .. message_issue.summary
  end
  return check("edit", status, with_message_evidence(message, messages))
end

local function client_supports_formatting(client)
  if type(client.supports_method) == "function" then
    return client:supports_method "textDocument/formatting"
  end
  return client.server_capabilities and client.server_capabilities.documentFormattingProvider or false
end

local function formatting_clients_for(bufnr)
  local clients = {}
  for _, client in ipairs(clients_for(bufnr)) do
    if client_supports_formatting(client) then
      table.insert(clients, client)
    end
  end
  return clients
end

local function format_on_save_applies(path)
  local config = type(lvim) == "table" and lvim.format_on_save
  if type(config) ~= "table" or config.enabled ~= true or type(config.pattern) ~= "table" then
    return false
  end

  for _, pattern in ipairs(config.pattern) do
    if type(pattern) == "string" and vim.fn.match(path, vim.fn.glob2regpat(pattern)) >= 0 then
      return true
    end
  end
  return false
end

local function unavailable_formatter_check(name, binary, mode)
  local status = mode == "smoke" and "skip" or "fail"
  return check("format", status, string.format("formatter=%s unavailable: %s not installed", name, binary))
end

local function format_check(entry, bufnr, requested_path, mode)
  if type(entry.format) ~= "string" or entry.format == "" then
    return nil
  end
  if not format_on_save_applies(entry.path) then
    return nil
  end

  local formatter_bin = formatter_bins[entry.format]
  if formatter_bin == nil then
    return unavailable_formatter_check(entry.format, "no executable mapping", mode)
  end
  if vim.fn.executable(formatter_bin) == 0 then
    return unavailable_formatter_check(entry.format, formatter_bin, mode)
  end

  local waited = vim.wait(5000, function()
    return #formatting_clients_for(bufnr) > 0
  end, 50)
  local formatting_clients = formatting_clients_for(bufnr)
  local formatting_client = formatting_clients[1]
  if not waited or formatting_client == nil then
    local attached = {}
    for _, client in ipairs(clients_for(bufnr)) do
      table.insert(attached, client.name)
    end
    return check(
      "format",
      "fail",
      string.format(
        "formatter=%s formatting client missing after wait=%s attached=%s",
        entry.format,
        tostring(waited),
        joined_names(attached)
      )
    )
  end

  local format_snapshot = message_snapshot()
  local ok, err = pcall(function()
    vim.cmd "silent write"
    vim.lsp.buf.format { async = false, timeout_ms = 5000, bufnr = bufnr }
  end)
  local messages = new_messages(format_snapshot)
  local message_issue = classify_runtime_messages(messages)
  local formatted_path = requested_path .. ".formatted"
  local has_formatted = vim.fn.filereadable(formatted_path) == 1
  local matches_formatted = true
  if has_formatted then
    matches_formatted = vim.deep_equal(
      vim.api.nvim_buf_get_lines(bufnr, 0, -1, false),
      vim.fn.readfile(formatted_path)
    )
  end

  local status = ok and matches_formatted and message_issue == nil and "pass" or "fail"
  local message = string.format("formatter=%s client=%s", entry.format, formatting_client.name)
  if has_formatted then
    message = message .. " baseline_match=" .. tostring(matches_formatted)
  end
  if not ok then
    message = message .. " error=" .. tostring(err)
  end
  if message_issue ~= nil then
    message = message_issue.label .. ": " .. message
      .. " cause=" .. message_issue.summary
  end
  return check("format", status, with_message_evidence(message, messages))
end

local function run_fixture(root, entry, mode, current_version)
  local skipped_for_version = version_check(entry, current_version)
  if skipped_for_version ~= nil then
    return { path = entry.path, ft_got = "", checks = { skipped_for_version } }
  end

  local path = root .. "/" .. entry.path
  local requested_path = vim.fn.fnamemodify(path, ":p")
  local checks = {}
  local readable = vim.fn.filereadable(requested_path) == 1
  local expected_lines = readable and vim.fn.readfile(requested_path) or {}

  vim.cmd("silent! enew!")
  vim.bo.filetype = ""
  vim.v.errmsg = ""

  local open_snapshot = message_snapshot()
  local opened, err = pcall(vim.cmd.edit, vim.fn.fnameescape(requested_path))
  local open_messages = new_messages(open_snapshot)
  local open_issue = classify_runtime_messages(open_messages)
  local current_path = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(0), ":p")
  local buffer_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local path_matches = current_path == requested_path
  local content_matches = readable and vim.deep_equal(buffer_lines, expected_lines)
  local open_status = readable and opened and path_matches and content_matches and open_issue == nil and "pass" or "fail"
  local open_message
  if open_issue ~= nil then
    open_message = "runtime error during open: " .. open_issue.summary
  elseif open_status == "pass" then
    open_message = string.format("readable file loaded into buffer with matching content (%d lines)", #buffer_lines)
  else
    open_message = string.format(
      "expected readable file to load into current buffer with matching content (readable=%s, edit=%s, path_match=%s, content_match=%s, buffer_lines=%d, error=%s)",
      tostring(readable),
      tostring(opened),
      tostring(path_matches),
      tostring(content_matches),
      #buffer_lines,
      opened and "" or tostring(err)
    )
  end
  table.insert(checks, check("opens", open_status, with_message_evidence(open_message, open_messages)))

  local ft_got = vim.bo.filetype
  table.insert(
    checks,
    check("filetype", ft_got == entry.ft and "pass" or "fail", string.format("expected %s, got %s", entry.ft, ft_got))
  )
  local bufnr = vim.api.nvim_get_current_buf()
  table.insert(checks, highlight_check(entry, bufnr))

  local lsp_check, healthy_check = lsp_checks(entry, bufnr, mode)
  if lsp_check ~= nil then
    table.insert(checks, lsp_check)
  end
  if healthy_check ~= nil then
    table.insert(checks, healthy_check)
  end
  table.insert(checks, edit_check(bufnr, expected_lines))

  local format_result = format_check(entry, bufnr, requested_path, mode)
  if format_result ~= nil then
    table.insert(checks, format_result)
  end

  return { path = entry.path, ft_got = ft_got, checks = checks }
end

local function run()
  local root = require_string("SMOKE_ROOT", SMOKE_ROOT)
  local mode = require_string("SMOKE_MODE", SMOKE_MODE)
  local current_version = current_nvim_version()
  local results = {}

  for _, entry in ipairs(selected_entries(load_manifest())) do
    table.insert(results, run_fixture(root, entry, mode, current_version))
  end

  return { nvim = version_string(current_version[1], current_version[2], current_version[3]), results = results }
end

local ok, result = xpcall(run, function(err)
  return debug.traceback(tostring(err), 2)
end)

write_report(ok and result or { runner_error = result, results = {} })
