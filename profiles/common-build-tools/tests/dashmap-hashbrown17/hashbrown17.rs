use dashmap::{DashMap, try_result::TryResult};
use std::borrow::Borrow;
use std::hash::{Hash, Hasher};
use std::sync::{Arc, Weak, atomic::{AtomicUsize, Ordering}};
use std::thread;

struct Key {
    id: u64,
    map: Weak<DashMap<Key, u64>>,
    locked_drops: Option<Arc<AtomicUsize>>,
}
impl Borrow<u64> for Key { fn borrow(&self) -> &u64 { &self.id } }
impl PartialEq for Key { fn eq(&self, other: &Self) -> bool { self.id == other.id } }
impl Eq for Key {}
impl Clone for Key { fn clone(&self) -> Self { panic!("intentional key clone panic") } }
impl Hash for Key { fn hash<H: Hasher>(&self, state: &mut H) { self.id.hash(state); } }
impl Drop for Key {
    fn drop(&mut self) {
        if let (Some(map), Some(count)) = (self.map.upgrade(), &self.locked_drops) {
            if matches!(map.try_get(&self.id), TryResult::Locked) {
                count.fetch_add(1, Ordering::SeqCst);
            }
        }
    }
}
fn key(map: &Arc<DashMap<Key, u64>>, id: u64, count: Option<Arc<AtomicUsize>>) -> Key {
    Key { id, map: Arc::downgrade(map), locked_drops: count }
}
#[test]
fn entry_drop_releases_guard_before_key_drop() {
    let map = Arc::new(DashMap::new());
    map.insert(key(&map, 7, None), 1);
    let locked = Arc::new(AtomicUsize::new(0));
    drop(map.entry(key(&map, 8, Some(locked.clone()))));
    drop(map.entry(key(&map, 7, Some(locked.clone()))));
    assert_eq!(locked.load(Ordering::SeqCst), 0);
    let guard = map.entry(key(&map, 7, Some(locked.clone()))).or_insert(2);
    assert_eq!(*guard, 1);
    drop(guard);
    // Stable DashMap drops the lookup key while the returned RefMut is held.
    assert_eq!(locked.load(Ordering::SeqCst), 1);
}
#[test]
fn clone_panic_drops_entry_before_guard_and_key() {
    let map = Arc::new(DashMap::new());
    let locked = Arc::new(AtomicUsize::new(0));
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        map.entry(key(&map, 9, Some(locked.clone()))).insert_entry(1);
    }));
    assert!(result.is_err());
    assert_eq!(locked.load(Ordering::SeqCst), 0);
    assert!(matches!(map.try_get(&9), TryResult::Absent));
}
#[test]
fn retained_iterator_items_survive_iterator_drop() {
    let map = DashMap::new();
    for i in 0..64 { map.insert(i, i * 2); }
    let mut iter = map.iter();
    let first = iter.next().unwrap();
    let (k, v) = (*first.key(), *first.value());
    drop(iter);
    assert_eq!((*first.key(), *first.value()), (k, v));
    assert!(matches!(map.try_get_mut(&k), TryResult::Locked));
    drop(first);
    assert!(matches!(map.try_get_mut(&k), TryResult::Present(_)));
    let mut iter = map.iter_mut();
    let mut first = iter.next().unwrap();
    let k = *first.key();
    drop(iter);
    *first += 1;
    assert!(matches!(map.try_get(&k), TryResult::Locked));
    drop(first);
    assert_eq!(*map.get(&k).unwrap(), k * 2 + 1);
}
#[test]
fn concurrent_insert_remove_resize_and_retain() {
    let map = Arc::new(DashMap::with_capacity(1));
    let workers: Vec<_> = (0..4).map(|t| {
        let map = map.clone();
        thread::spawn(move || {
            for i in 0..1000 {
                let key = t * 1000 + i;
                map.insert(key, key);
                assert_eq!(map.remove(&key).unwrap().1, key);
                map.insert(key, key + 1);
            }
        })
    }).collect();
    for worker in workers { worker.join().unwrap(); }
    assert_eq!(map.len(), 4000);
    map.retain(|k, v| { *v += 1; *k % 2 == 0 });
    assert_eq!(map.len(), 2000);
    for i in (0..4000).step_by(2) { assert_eq!(*map.get(&i).unwrap(), i + 2); }
}
#[cfg(feature="rayon")]
#[test]
fn parallel_mutate_all_values() {
    use rayon::prelude::*;
    let map = DashMap::new();
    for i in 0..1024 { map.insert(i, i); }
    let retained: Vec<_> = map.par_iter().collect();
    let k = *retained[0].key();
    assert!(matches!(map.try_get_mut(&k), TryResult::Locked));
    drop(retained);
    map.par_iter_mut().for_each(|mut v| *v += 1);
    assert_eq!(map.par_iter().map(|v| *v).sum::<usize>(), (0..1024).map(|i| i + 1).sum());
}
