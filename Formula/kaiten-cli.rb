class KaitenCli < Formula
  include Language::Python::Virtualenv

  desc "Command-line interface for Kaiten"
  homepage "https://github.com/ViktorOgnev/kaiten-cli"
  url "https://files.pythonhosted.org/packages/35/20/321e7d33f0611631201a600e1d5fa0235e03944a218f3389c87376a74220/kaiten_cli-0.3.6.tar.gz"
  sha256 "9dc2635043a874273cd6c58ed388d1c36560d167ea97e814d0c697ebf277b52e"
  license "MIT"

  depends_on "node"
  depends_on "python@3.15"

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/a1/98/7e457a3b014976887a050561955c0b76e1e7e2d6e27b78ecef2ef80518f2/anyio-4.16.0.tar.gz"
    sha256 "59bb03251907983d1603d27c3087ddb1e93299ea2163adcdba37899a4fb12ffb"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/fd/11/b524cbd9bbdaca58608e4cf4053fd463417549e1959fa8d3aa18319f9555/certifi-2026.10.23.tar.gz"
    sha256 "a9895e6e2758b371e0545e321a3a8fd1fcfd9829ada8824a936dfb16aaaf36cd"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/45/37/edbf1b0707709013c0cf2e8317e03d97ed29bf4cac709fe328904ae92a38/click-8.5.1.tar.gz"
    sha256 "9bbfada76703fd1d784b83eea012e3e8c6a001a876543ef104fa56aaaeb072b4"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/01/ee/02a2c011bdab74c6fb3c75474d40b3052059d95df7e73351460c8588d963/h11-0.16.0.tar.gz"
    sha256 "4e35b956cf45792e4caa5885e69fba00bdbc6ffafbfa020300e549b208ee5ff1"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/06/94/82699a10bca87a5556c9c59b5963f2d039dbd239f25bc2a63907a05a14cb/httpcore-1.0.9.tar.gz"
    sha256 "6e34463af53fd2ab5d807f399a9b45ea31c3dfa2276f15a2c3f00afff6e176e8"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/b1/df/48c586a5fe32a0f01324ee087459e112ebb7224f646c0b5023f5e79e9956/httpx-0.28.1.tar.gz"
    sha256 "75e98c5f16b0f35b567856f597f06ff2270a374470a5c2392242528e3e3e42fc"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/f5/08/8eea9d4b8302028f3abb2c0813953f7aec26d33b7a8960ed760e65ff29fa/idna-3.20.tar.gz"
    sha256 "a7db850025b95ded1eae8a46181a1a6c56c92c96f0e2b005d9ff8dc0210cab44"
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/a6/2c/ec57eede0db493e61443c76ac7b4d24e94a24050afb3d598bf3678487f75/platformdirs-4.14.7.tar.gz"
    sha256 "5472257c1cf97a14658af52997011c7e59e4aebf3a24950b973c11b579e1b074"
  end

  def install
    cd "js/document-yjs" do
      system "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"
      system "npm", "run", "build"
    end
    virtualenv_install_with_resources
  end

  test do
    ENV["KAITEN_DOMAIN"] = ""
    ENV["KAITEN_TOKEN"] = ""
    ENV["KAITEN_CLI_CONFIG_PATH"] = (testpath/"config.json").to_s
    ENV["KAITEN_TRACE_FILE"] = (testpath/"trace.jsonl").to_s
    assert_match version.to_s, shell_output("#{bin}/kaiten --locale ru --version")
    assert_match "--locale", shell_output("#{bin}/kaiten --locale ru --help")
    result = JSON.parse(shell_output("#{bin}/kaiten --locale ru --read-only --json search-tools cards"))
    assert result.fetch("success")
    assert_includes result.fetch("data").map { |tool| tool.fetch("canonical_name") }, "cards.list"
    assert_equal 0, result.fetch("stats").fetch("http_request_count")
    assert_match "gateway", shell_output("#{bin}/kaiten-agent-gateway --help")
    python = libexec/"bin/python"
    source_script = "from kaiten_cli.update_check import detect_install_source; print(detect_install_source())"
    source = shell_output("#{python} -c '#{source_script}'")
    assert_equal "None", source.strip
    helper = libexec/"lib/python3.15/site-packages/kaiten_cli/assets/document_yjs.cjs"
    assert_path_exists helper
    system formula_opt_bin("node")/"node", "--check", helper
    warnings = testpath/"node-warnings.log"
    output = pipe_output(
      "#{formula_opt_bin("node")}/node --redirect-warnings=#{warnings} #{helper} 2>&1", "{}\n", 1
    )
    begin
      result = JSON.parse(output)
    rescue JSON::ParserError
      flunk "Unexpected helper output: #{output}"
    end
    assert_equal "unsupported_schema", result.fetch("code")
    puts warnings.read if warnings.exist?
    shell_output("#{bin}/kaiten --locale ru --json trace summarize --file #{testpath}/trace.jsonl")
  end
end
