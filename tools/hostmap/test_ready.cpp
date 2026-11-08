#include "ready.hpp"
#include <cassert>
#include <iostream>

int main() {
    hostmap::Ready ready;
    ready.sync("roster1", {1,2,3,4,5}, true);
    assert(!ready.vote(1));
    assert(!ready.vote(1)); // One player cannot vote repeatedly for others.
    assert(!ready.vote(6)); // Observer not in the human playing roster.
    assert(!ready.vote(2));
    assert(!ready.vote(3));
    assert(!ready.vote(4));
    assert(ready.vote(5)); // Five humans can start a map with ten available slots.
    ready.sync("roster2", {1,2,3,4}, true);
    assert(!ready.complete()); // Leaving clears earlier votes.
    ready.vote(1); ready.vote(2); ready.vote(3);
    assert(ready.vote(4));
    ready.sync("moved-slot", {1,2,3,4}, true);
    assert(!ready.complete()); // Same people in changed slots must confirm again.
    ready.sync("downloading", {1,2}, false);
    ready.vote(1); ready.vote(2);
    assert(!ready.complete());
    ready.sync("downloading", {1,2}, true);
    assert(!ready.complete()); // No votes accepted before download/auth is complete.
    ready.vote(1); assert(ready.vote(2));
    ready.sync("empty", {}, true);
    assert(!ready.complete());
    std::cout << "HOSTMAP_READY_TESTS_OK\n";
}
