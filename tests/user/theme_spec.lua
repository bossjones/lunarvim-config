local theme = require "user.theme"

describe("theme", function()
  describe("colors", function()
    it("has all four palettes", function()
      assert.is_table(theme.colors.tokyonight_colors)
      assert.is_table(theme.colors.rose_pine_colors)
      assert.is_table(theme.colors.catppuccin_colors)
      assert.is_table(theme.colors.kanagawa_colors)
    end)

    it("each palette has bg and fg", function()
      for name, palette in pairs(theme.colors) do
        assert.is_not_nil(palette.bg, name .. " should have bg")
        assert.is_not_nil(palette.fg, name .. " should have fg")
      end
    end)

    it("each palette has git sub-table with add/delete/change", function()
      for name, palette in pairs(theme.colors) do
        assert.is_table(palette.git, name .. " should have git table")
        assert.is_not_nil(palette.git.add, name .. ".git.add should exist")
        assert.is_not_nil(palette.git.delete, name .. ".git.delete should exist")
        assert.is_not_nil(palette.git.change, name .. ".git.change should exist")
      end
    end)

    it("hex color values match #RRGGBB pattern", function()
      local hex_pattern = "^#%x%x%x%x%x%x$"
      for name, palette in pairs(theme.colors) do
        assert.is_truthy(
          string.match(palette.bg, hex_pattern),
          name .. ".bg = " .. palette.bg .. " should be hex color"
        )
        assert.is_truthy(
          string.match(palette.fg, hex_pattern),
          name .. ".fg = " .. palette.fg .. " should be hex color"
        )
        assert.is_truthy(
          string.match(palette.git.add, hex_pattern),
          name .. ".git.add = " .. palette.git.add .. " should be hex color"
        )
      end
    end)
  end)

  describe("current_colors", function()
    it("returns a table", function()
      local colors = theme.current_colors()
      assert.is_table(colors)
    end)

    it("returned palette has bg, fg, and git", function()
      local colors = theme.current_colors()
      assert.is_not_nil(colors.bg)
      assert.is_not_nil(colors.fg)
      assert.is_table(colors.git)
      assert.is_not_nil(colors.git.add)
      assert.is_not_nil(colors.git.delete)
      assert.is_not_nil(colors.git.change)
    end)

    it("returns one of the known palettes", function()
      local colors = theme.current_colors()
      local known = {
        theme.colors.tokyonight_colors,
        theme.colors.rose_pine_colors,
        theme.colors.catppuccin_colors,
        theme.colors.kanagawa_colors,
      }
      local found = false
      for _, palette in ipairs(known) do
        if palette.bg == colors.bg and palette.fg == colors.fg then
          found = true
          break
        end
      end
      assert.is_true(found, "current_colors() should return one of the known palettes")
    end)
  end)
end)
