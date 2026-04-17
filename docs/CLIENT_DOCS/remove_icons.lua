-- Removes decorative icons/emojis and inline images from documents.

local function strip_icon_chars(s)
  -- Remove common emoji/symbol ranges frequently used as icons.
  s = s:gsub("[%z\1-\127\194-\244][\128-\191]*", function(ch)
    local b1 = ch:byte(1)
    if not b1 then
      return ch
    end

    -- Fast path for plain ASCII
    if b1 < 128 then
      return ch
    end

    local cp = utf8.codepoint(ch)
    if not cp then
      return ch
    end

    -- Emoji + dingbats + misc symbols commonly used as icons.
    if (cp >= 0x1F300 and cp <= 0x1FAFF) or
       (cp >= 0x2600 and cp <= 0x27BF) or
       (cp >= 0x2190 and cp <= 0x21FF) then
      return ""
    end

    return ch
  end)

  -- Remove variation selectors and zero-width joiners used in emoji sequences.
  s = s:gsub(utf8.char(0xFE0F), "")
  s = s:gsub(utf8.char(0x200D), "")
  return s
end

function Str(el)
  local cleaned = strip_icon_chars(el.text)
  if cleaned == "" then
    return {}
  end
  if cleaned ~= el.text then
    return pandoc.Str(cleaned)
  end
  return el
end

function Image(_)
  -- Remove inline/badge/icon images from output docs.
  return {}
end
