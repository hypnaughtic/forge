class ForgeInit < Formula
  include Language::Python::Virtualenv

  desc "Project initialization tool for Claude Code CLI agent teams"
  homepage "https://github.com/Rushabh1798/forge"
  url "https://github.com/Rushabh1798/forge/archive/refs/tags/v2.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "click" do
    url "https://files.pythonhosted.org/packages/click/click-8.1.7.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/rich/rich-13.7.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/pyyaml/PyYAML-6.0.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/jinja2/Jinja2-3.1.3.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/pydantic/pydantic-2.6.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "questionary" do
    url "https://files.pythonhosted.org/packages/questionary/questionary-2.0.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "forge", shell_output("#{bin}/forge --version")
  end
end
