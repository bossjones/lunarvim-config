local ok, schemastore = pcall(require, "schemastore")

local opts = {
  settings = {
    json = {
      validate = { enable = true },
      schemas = ok and schemastore.json.schemas() or {},
    },
  },
}

require("lvim.lsp.manager").setup("jsonls", opts)

vim.opt_local.tabstop = 2
vim.opt_local.shiftwidth = 2
vim.opt_local.expandtab = true
