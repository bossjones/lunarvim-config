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
        assert.is_truthy(
          string.match(palette.git.delete, hex_pattern),
          name .. ".git.delete = " .. palette.git.delete .. " should be hex color"
        )
        assert.is_truthy(
          string.match(palette.git.change, hex_pattern),
          name .. ".git.change = " .. palette.git.change .. " should be hex color"
        )
      end
    end)
  end)

  describe("current_colors", function()
    local original_date

    before_each(function()
      original_date = os.date
    end)

    after_each(function()
      os.date = original_date
    end)

    it("returns rose_pine_colors between 1-9 AM", function()
      os.date = function()
        return { hour = 5 }
      end
      local colors = theme.current_colors()
      assert.are.equal(theme.colors.rose_pine_colors.bg, colors.bg)
    end)

    it("returns tokyonight_colors between 9 AM-5 PM", function()
      os.date = function()
        return { hour = 12 }
      end
      local colors = theme.current_colors()
      assert.are.equal(theme.colors.tokyonight_colors.bg, colors.bg)
    end)

    it("returns catppuccin_colors between 5-9 PM", function()
      os.date = function()
        return { hour = 18 }
      end
      local colors = theme.current_colors()
      assert.are.equal(theme.colors.catppuccin_colors.bg, colors.bg)
    end)

    it("returns kanagawa_colors between 9 PM-midnight", function()
      os.date = function()
        return { hour = 22 }
      end
      local colors = theme.current_colors()
      assert.are.equal(theme.colors.kanagawa_colors.bg, colors.bg)
    end)

    it("returned palette has bg, fg, and git", function()
      os.date = function()
        return { hour = 12 }
      end
      local colors = theme.current_colors()
      assert.is_not_nil(colors.bg)
      assert.is_not_nil(colors.fg)
      assert.is_table(colors.git)
      assert.is_not_nil(colors.git.add)
      assert.is_not_nil(colors.git.delete)
      assert.is_not_nil(colors.git.change)
    end)
  end)
end)
