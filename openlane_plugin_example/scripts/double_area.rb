input = ARGV[0]
output = ARGV[1]

input_str = File.read(input)

die_area_rx = /DIEAREA\s*\(\s*(\d+)\s+(\d+)\s*\)\s*\(\s*(\d+)\s+(\d+)\s*\)/

match = die_area_rx.match(input_str)
    
if match.nil?
    STDERR.puts "No DIEAREA statement found."
    exit(-1)
end

literal = match[0]
lx, ly, ux, uy = match[1].to_i, match[2].to_i, match[3].to_i, match[4].to_i

File.open(output, "w") { |f|
    f << input_str.gsub(literal, "DIEAREA ( #{lx} #{ly} ) ( #{ux * 2} #{uy * 2} )")
}
