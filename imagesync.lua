-- imagesync.lua
local args = {...}
local pastebin_id = args[1]


-- Checking args
if not pastebin_id then
    print("Use     : imagesync <PASTEBIN_ID> ")
    print("Example : imagesync pmF7EYpT")
    return
end

-- Loads monitor
local mon = peripheral.find("monitor")
if not mon then
    print("ERROR: No monitor found !")
    return
end

mon.setTextScale(0.5)
mon.clear()

-- Cache system
local content = ""
local dir_path = "Images"
local file_path = dir_path .. "/" .. pastebin_id .. ".txt"

-- Checking local cache
if fs.exists(file_path) then
    print("Image found in cache, loading...")
    local file = fs.open(file_path, "r")
    content = file.readAll()
    file.close()
else
    -- Pastebin download
    print("Connecting to Pastebin (" .. pastebin_id .. ")...")
    local url = "https://pastebin.com/raw/" .. pastebin_id
    local response, err = http.get(url)

    if not response then
        print("Error while downloading from pastebin...")
        print(err)
        return
    end

    content = response.readAll()
    response.close()

    if string.len(content) == 0 then
        print("Error: File is empty")
        return
    end

    -- Creating "Images/" if not exists
    if not fs.exists(dir_path) then
        fs.makeDir(dir_path)
    end

    -- Save image to Images/
    print("Saving locally...")
    local file = fs.open(file_path, "w")
    file.write(content)
    file.close()
end

-- Render using term.blit
local y = 1
for line in string.gmatch(content, "[^\r\n]+") do
    mon.setCursorPos(1, y)
    local empty_text = string.rep(" ", #line)
    local text_color = string.rep("f", #line)  -- Text is empty...
    
    mon.blit(empty_text, text_color, line)
    y = y + 1
end

print("Task should be done")
