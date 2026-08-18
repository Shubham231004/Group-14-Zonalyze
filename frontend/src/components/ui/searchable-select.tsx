import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export interface SearchableSelectOption {
  value: string;
  label: string;
}

interface SearchableSelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SearchableSelectOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  /** When true, the user can commit a value they typed even if it is not in the list. */
  allowCustomValue?: boolean;
  emptyText?: string;
  triggerClassName?: string;
}

/**
 * Pick-or-type select. Users can choose from the list OR type their own value
 * (when allowCustomValue is set) — the same freedom for cities and business ideas.
 */
export function SearchableSelect({
  value,
  onValueChange,
  options,
  placeholder = "Select...",
  searchPlaceholder = "Search or type...",
  allowCustomValue = false,
  emptyText = "No match found.",
  triggerClassName,
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");

  const selected = options.find((option) => option.value === value);
  const displayLabel = selected?.label ?? (value || placeholder);
  const trimmed = query.trim();
  const showCustomOption =
    allowCustomValue &&
    trimmed.length > 0 &&
    !options.some((option) => option.value.toLowerCase() === trimmed.toLowerCase());

  const commit = (nextValue: string) => {
    onValueChange(nextValue);
    setOpen(false);
    setQuery("");
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between bg-background/50 border-white/10 font-mono text-sm h-11 rounded-xl",
            triggerClassName,
          )}
        >
          <span className={cn("truncate text-left", !value && "text-muted-foreground")}>
            {displayLabel}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0 bg-card border-white/10"
        align="start"
        style={{ width: "var(--radix-popover-trigger-width)" }}
      >
        <Command>
          <CommandInput
            placeholder={searchPlaceholder}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            <CommandEmpty>
              {allowCustomValue
                ? "Keep typing, then pick “Use what you typed”."
                : emptyText}
            </CommandEmpty>
            {showCustomOption ? (
              <CommandGroup heading="Use what you typed">
                <CommandItem value={trimmed} onSelect={() => commit(trimmed)}>
                  Use “{trimmed}”
                </CommandItem>
              </CommandGroup>
            ) : null}
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  // Keyed by value AND label: two Ontario municipalities share the
                  // name "Hamilton" (the city and the township), so keying by value
                  // alone gave React duplicate keys — and duplicate keys let it
                  // commit a DIFFERENT option than the one clicked. The pair is
                  // unique even if a future catalog repeats one half of it.
                  key={`${option.value}::${option.label}`}
                  value={option.label}
                  onSelect={() => commit(option.value)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === option.value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {option.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
