require "nokogiri"
require "pathname"
require "uri"

root = Pathname.new(ARGV.fetch(0, "_site")).expand_path
baseurl = ARGV.fetch(1, "").delete_suffix("/")
abort "Build directory does not exist: #{root}" unless root.directory?
errors = []
documents = {}
files = root.glob("**/*.html")
errors << "Build contains no HTML pages" if files.empty?

files.each do |file|
  document = Nokogiri::HTML(file.read(encoding: "UTF-8"))
  documents[file.to_s] = document
  errors << "#{file}: missing page title" if document.at_css("title")&.text.to_s.strip.empty?
  # Markdown tutorials intentionally demonstrate headings; only reject a repeated page title.
  hero_title = document.at_css(".hero h1")&.text
  if hero_title && document.css(".article h1").any? { |heading| heading.text == hero_title }
    errors << "#{file}: article repeats the page title"
  end
end

check_link = lambda do |file, reference|
  next if reference.empty? || reference.match?(%r{\A(?:[a-z][a-z0-9+.-]*:|//)}i)
  path, fragment = reference.split("#", 2)
  path = URI::DEFAULT_PARSER.unescape(path.split("?", 2).first.to_s)
  if path.start_with?("/") && !baseurl.empty?
    unless path == baseurl || path.start_with?(baseurl + "/")
      errors << "#{file}: link misses baseurl: #{reference}"
      next
    end
    path = path.delete_prefix(baseurl)
  end
  target = if path.empty?
    file
  elsif path.start_with?("/")
    root.join(path.delete_prefix("/"))
  else
    file.dirname.join(path)
  end
  target = target.cleanpath
  unless target.to_s == root.to_s || target.to_s.start_with?(root.to_s + File::SEPARATOR)
    errors << "#{file}: link escapes build directory: #{reference}"
    next
  end
  target = target.join("index.html") if target.directory?
  unless target.file?
    errors << "#{file}: missing local resource: #{reference}"
    next
  end
  next if fragment.nil? || fragment.empty? || target.extname != ".html"
  target_document = documents[target.to_s] ||= Nokogiri::HTML(target.read(encoding: "UTF-8"))
  id = URI::DEFAULT_PARSER.unescape(fragment)
  unless target_document.css("[id], a[name]").any? { |node| node["id"] == id || node["name"] == id }
    errors << "#{file}: missing anchor: #{reference}"
  end
end

documents.dup.each do |filename, document|
  file = Pathname.new(filename)
  document.css("[href], [src]").each do |node|
    %w[href src].each { |attribute| check_link.call(file, node[attribute]) if node[attribute] }
  end
  document.css("[style]").each do |node|
    node["style"].scan(/url\((['"])(.*?)\1\)/).each do |_, reference|
      check_link.call(file, reference)
    end
  end
end

feed = root.join("feed.xml")
begin
  rss = Nokogiri::XML(feed.read) { |config| config.strict.nonet }
  errors << "RSS has no articles" if rss.xpath("/rss/channel/item").empty?
rescue Nokogiri::XML::SyntaxError, Errno::ENOENT => error
  errors << "Invalid RSS: #{error.message}"
end

abort errors.join("\n") unless errors.empty?
puts "Checked #{files.length} HTML pages, local resources, anchors, and RSS."
