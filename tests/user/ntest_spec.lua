local ntest = require "user.ntest"

describe("ntest", function()
  describe("get_env", function()
    local test_env_path = ".env"
    local original_dir

    before_each(function()
      original_dir = vim.fn.getcwd()
      -- Use a temp directory so we don't pollute the repo
      local tmp = vim.fn.tempname()
      vim.fn.mkdir(tmp, "p")
      vim.cmd("cd " .. tmp)
    end)

    after_each(function()
      -- Clean up .env if it exists
      if vim.fn.filereadable(test_env_path) == 1 then
        vim.fn.delete(test_env_path)
      end
      vim.cmd("cd " .. original_dir)
    end)

    it("returns empty table when no .env file exists", function()
      local env = ntest.get_env()
      assert.is_table(env)
      assert.same({}, env)
    end)

    it("parses KEY=value pairs", function()
      vim.fn.writefile({ "FOO=bar", "BAZ=qux" }, test_env_path)
      local env = ntest.get_env()
      assert.equals("bar", env.FOO)
      assert.equals("qux", env.BAZ)
    end)

    it("handles double-quoted values", function()
      vim.fn.writefile({ 'MY_VAR="hello world"' }, test_env_path)
      local env = ntest.get_env()
      assert.equals("hello world", env.MY_VAR)
    end)

    it("handles single-quoted values", function()
      vim.fn.writefile({ "MY_VAR='hello world'" }, test_env_path)
      local env = ntest.get_env()
      assert.equals("hello world", env.MY_VAR)
    end)
  end)
end)
