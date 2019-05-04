# Machi

[Machi](https://github.com/basho/machi) port of its persistent storage
to Python, but without replication. Its design borrowed, but file
formats are not compatible.

Two Files:

1. Index file
2. Data file

Index file consists of `maxlen` entries:

```
  0    8         24   28   32 bytes
  +----+----+----+----+----+
  |gen |off |len |CRC |st  |
  +----+----+----+----+----+
```

So the file length of index file is `32 * maxlen` bytes. For one
million maxlen RAQ the file size will be 36MiB. Each items means

- `gen`: Generation of the data file where the payload stored in.
- `off` `len`: Offset and length in the data file where the payload stored in.
- `CRC`: CRC32 checksum of the payload.
- `st`: State of the entry; `-1` for trimmed, `0` for non-existent, `1` for existent entry.

Data file has no formats, but just bunch of blobs concatinated.  Data
files has numbers (`gen` in index), which is represented by their file
names. Data files may be removed when all entries are trimmed.

## License

MIT License, (C) Kota UENISHI 2019.
