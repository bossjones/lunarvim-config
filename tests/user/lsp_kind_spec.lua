local lsp_kind = require("user.lsp_kind")

describe("lsp_kind", function()
  describe("icons", function()
    it("has expected diagnostic keys", function()
      assert.is_not_nil(lsp_kind.icons.error)
      assert.is_not_nil(lsp_kind.icons.warn)
      assert.is_not_nil(lsp_kind.icons.info)
      assert.is_not_nil(lsp_kind.icons.hint)
    end)

    it("has utility icons", function()
      assert.is_not_nil(lsp_kind.icons.clock)
      assert.is_not_nil(lsp_kind.icons.git)
      assert.is_not_nil(lsp_kind.icons.magic)
    end)

    it("values are non-empty strings", function()
      for key, value in pairs(lsp_kind.icons) do
        assert.is_string(value, "icons." .. key .. " should be a string")
        assert.is_true(#value > 0, "icons." .. key .. " should be non-empty")
      end
    end)
  end)

  describe("cmp_kind", function()
    it("has LSP completion kinds", function()
      local expected_kinds = { "Function", "Method", "Variable", "Class", "Field", "Struct", "Module" }
      for _, kind in ipairs(expected_kinds) do
        assert.is_not_nil(lsp_kind.cmp_kind[kind], "cmp_kind." .. kind .. " should exist")
      end
    end)

    it("values are non-empty strings", function()
      for key, value in pairs(lsp_kind.cmp_kind) do
        assert.is_string(value, "cmp_kind." .. key .. " should be a string")
        assert.is_true(#value > 0, "cmp_kind." .. key .. " should be non-empty")
      end
    end)
  end)

  describe("nvim_tree_icons", function()
    it("has git sub-table", function()
      assert.is_table(lsp_kind.nvim_tree_icons.git)
      assert.is_not_nil(lsp_kind.nvim_tree_icons.git.added)
      assert.is_not_nil(lsp_kind.nvim_tree_icons.git.deleted)
      assert.is_not_nil(lsp_kind.nvim_tree_icons.git.modified)
    end)

    it("has folder sub-table", function()
      assert.is_table(lsp_kind.nvim_tree_icons.folder)
      assert.is_not_nil(lsp_kind.nvim_tree_icons.folder.default)
      assert.is_not_nil(lsp_kind.nvim_tree_icons.folder.open)
    end)
  end)

  describe("numbers", function()
    it("has 10 entries", function()
      assert.equals(10, #lsp_kind.numbers)
    end)

    it("values are non-empty strings", function()
      for i, value in ipairs(lsp_kind.numbers) do
        assert.is_string(value, "numbers[" .. i .. "] should be a string")
        assert.is_true(#value > 0, "numbers[" .. i .. "] should be non-empty")
      end
    end)
  end)

  describe("symbols_outline", function()
    it("has expected keys", function()
      local expected_keys = { "File", "Module", "Class", "Method", "Function", "Variable", "Constant", "Struct" }
      for _, key in ipairs(expected_keys) do
        assert.is_not_nil(lsp_kind.symbols_outline[key], "symbols_outline." .. key .. " should exist")
      end
    end)
  end)
end)
